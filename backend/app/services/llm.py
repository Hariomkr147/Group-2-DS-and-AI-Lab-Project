"""LLM provider switch: choose the provider by env var or per request.

Env:
  LLM_PROVIDER   gemini (default) | openai | anthropic | ollama
  gemini:     GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GEMINI_MODEL   (Google ADC)
  openai:     OPENAI_API_KEY, OPENAI_MODEL, optional OPENAI_BASE_URL
  anthropic:  ANTHROPIC_API_KEY, ANTHROPIC_MODEL
  ollama:     OLLAMA_BASE_URL (default http://localhost:11434/v1), OLLAMA_MODEL

Each SDK is imported late, so only the SDK for the provider you use must be installed.
Callers use: p = get_provider(name_or_None); p.ready(); p.generate(...); p.stream(...); p.model
"""
import os

from fastapi import HTTPException

PROVIDERS = ("gemini", "openai", "anthropic", "ollama")
DEFAULT_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
_cache: dict[str, "Provider"] = {}


def _need(var: str, provider: str) -> str:
    val = os.environ.get(var)
    if not val:
        raise HTTPException(503, f"LLM provider '{provider}' is not configured (set {var})")
    return val


class Provider:
    name = ""
    model = ""

    def ready(self) -> None:
        """Create the client now so a missing config gives a real 503 before streaming starts."""
        raise NotImplementedError

    def generate(self, prompt: str, system: str | None, max_tokens: int) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, system: str | None, max_tokens: int):
        raise NotImplementedError


class Gemini(Provider):
    name = "gemini"

    def __init__(self):
        self.model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
        self.location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        self._client = None

    def ready(self):
        if self._client is None:
            import google.auth
            from google import genai
            try:
                _, adc_project = google.auth.default()
            except Exception as e:
                raise HTTPException(503, "LLM provider 'gemini' is not configured (no Google ADC credentials)") from e
            project = os.environ.get("GOOGLE_CLOUD_PROJECT") or adc_project
            if not project:
                raise HTTPException(503, "LLM provider 'gemini' is not configured (set GOOGLE_CLOUD_PROJECT)")
            self._client = genai.Client(vertexai=True, project=project, location=self.location)

    def _cfg(self, system, max_tokens):
        from google.genai import types
        return types.GenerateContentConfig(system_instruction=system, max_output_tokens=max_tokens)

    def generate(self, prompt, system, max_tokens):
        self.ready()
        resp = self._client.models.generate_content(
            model=self.model, contents=prompt, config=self._cfg(system, max_tokens))
        return resp.text or ""

    def stream(self, prompt, system, max_tokens):
        self.ready()
        for chunk in self._client.models.generate_content_stream(
                model=self.model, contents=prompt, config=self._cfg(system, max_tokens)):
            if chunk.text:
                yield chunk.text


class OpenAICompatible(Provider):
    """OpenAI, and anything speaking the same API (Ollama, OpenRouter, Groq...) via base_url."""

    def __init__(self, name: str):
        self.name = name
        self._client = None
        if name == "ollama":
            self.model = os.environ.get("OLLAMA_MODEL", "llama3.1")
            self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        else:
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            self.base_url = os.environ.get("OPENAI_BASE_URL")

    def ready(self):
        if self._client is None:
            from openai import OpenAI
            key = "ollama" if self.name == "ollama" else _need("OPENAI_API_KEY", self.name)
            self._client = OpenAI(api_key=key, base_url=self.base_url)

    def _messages(self, prompt, system):
        msgs = [{"role": "system", "content": system}] if system else []
        return msgs + [{"role": "user", "content": prompt}]

    def generate(self, prompt, system, max_tokens):
        self.ready()
        r = self._client.chat.completions.create(
            model=self.model, messages=self._messages(prompt, system), max_tokens=max_tokens)
        return r.choices[0].message.content or ""

    def stream(self, prompt, system, max_tokens):
        self.ready()
        for chunk in self._client.chat.completions.create(
                model=self.model, messages=self._messages(prompt, system), max_tokens=max_tokens, stream=True):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class Anthropic(Provider):
    name = "anthropic"

    def __init__(self):
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
        self._client = None

    def ready(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=_need("ANTHROPIC_API_KEY", self.name))

    def _kw(self, prompt, system, max_tokens):
        kw = dict(model=self.model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
        if system:
            kw["system"] = system
        return kw

    def generate(self, prompt, system, max_tokens):
        self.ready()
        r = self._client.messages.create(**self._kw(prompt, system, max_tokens))
        return "".join(b.text for b in r.content if b.type == "text")

    def stream(self, prompt, system, max_tokens):
        self.ready()
        with self._client.messages.stream(**self._kw(prompt, system, max_tokens)) as s:
            yield from s.text_stream


def get_provider(name: str | None = None) -> Provider:
    name = (name or DEFAULT_PROVIDER).lower()
    if name not in PROVIDERS:
        raise HTTPException(400, f"Unknown LLM provider '{name}'. Choose one of: {', '.join(PROVIDERS)}")
    if name not in _cache:
        _cache[name] = {"gemini": Gemini, "anthropic": Anthropic}.get(name, lambda: OpenAICompatible(name))()
    return _cache[name]


def generate(prompt: str, system: str | None = None, max_tokens: int = 512, provider: str | None = None) -> str:
    p = get_provider(provider)
    try:
        return p.generate(prompt, system, max_tokens)
    except HTTPException:
        raise
    except Exception as e:  # network, quota, bad key, API not enabled
        raise HTTPException(502, f"LLM request failed ({p.name}): {type(e).__name__}") from e
