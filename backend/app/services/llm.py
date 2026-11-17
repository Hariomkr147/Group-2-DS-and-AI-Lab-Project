"""LLM provider switch: choose the provider by env var or per request.

Env:
  LLM_PROVIDER   gemini (default) | openai | anthropic | ollama | qwen_finetuned
  qwen_finetuned:  QWEN_URL, QWEN_API_KEY (printed by the hosting notebook), optional QWEN_TIMEOUT
  gemini:     GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GEMINI_MODEL   (Google ADC)
  openai:     OPENAI_API_KEY, OPENAI_MODEL, optional OPENAI_BASE_URL
  anthropic:  ANTHROPIC_API_KEY, ANTHROPIC_MODEL
  ollama:     OLLAMA_BASE_URL (default http://localhost:11434/v1), OLLAMA_MODEL

Each SDK is imported late, so only the SDK for the provider you use must be installed.
Callers use: p = get_provider(name_or_None); p.ready(); p.generate(...); p.stream(...); p.model
"""
import os

from fastapi import HTTPException

PROVIDERS = ("gemini", "openai", "anthropic", "ollama", "qwen_finetuned")
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


class QwenFinetuned(Provider):
    """Our fine-tuned Qwen3.5-4B Socratic tutor. Replies are at most 96 new tokens. QWEN_URL picks the host:

    - a Hugging Face Space (https://<name>.hf.space, built from backend/model_hosting/hf-space),
      with a Hugging Face token of the Space owner in QWEN_API_KEY;
    - or the Kaggle notebook's tunnel URL (hosting-qwen.ipynb) with the key that notebook prints.
    """
    name = "qwen_finetuned"
    model = "qwen3.5-4b-socratic-tutor"
    MAX_NEW_TOKENS = 96

    def ready(self):
        _need("QWEN_URL", self.name)
        _need("QWEN_API_KEY", self.name)

    def _from_space(self, prompt, system, timeout):
        """Gradio API: one call queues the request, a second call reads the result as server-sent events."""
        import json
        import urllib.request
        url = os.environ["QWEN_URL"].rstrip("/") + "/gradio_api/call/predict"
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["QWEN_API_KEY"]}
        queued = urllib.request.Request(url, data=json.dumps({"data": [system or "", prompt]}).encode(), headers=headers)
        with urllib.request.urlopen(queued, timeout=timeout) as response:
            event_id = json.load(response)["event_id"]
        event = ""
        with urllib.request.urlopen(urllib.request.Request(f"{url}/{event_id}", headers=headers), timeout=timeout) as response:
            for line in response.read().decode().splitlines():
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:") and event == "complete":
                    return (json.loads(line[5:])[0] or "").strip()
                elif line.startswith("data:") and event == "error":
                    raise RuntimeError(f"Space returned an error: {line[5:].strip()[:200]}")   # e.g. GPU quota used up
        raise RuntimeError("Space returned no reply")

    def generate(self, prompt, system, max_tokens):
        import json
        import urllib.request
        self.ready()
        if ".hf.space" in os.environ["QWEN_URL"]:
            return self._from_space(prompt, system, float(os.environ.get("QWEN_TIMEOUT", "60")))
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {"messages": messages, "max_new_tokens": min(max_tokens, self.MAX_NEW_TOKENS)}
        request = urllib.request.Request(
            os.environ["QWEN_URL"].rstrip("/") + "/predict", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["QWEN_API_KEY"]})
        with urllib.request.urlopen(request, timeout=float(os.environ.get("QWEN_TIMEOUT", "60"))) as response:
            result = json.load(response)
        if result.get("protocol_flags"):   # the model wrote a second speaker's turn; do not show it
            raise ValueError("Qwen reply failed the server's protocol check")
        return (result.get("text") or "").strip()

    def stream(self, prompt, system, max_tokens):
        yield self.generate(prompt, system, max_tokens)   # the server does not stream


def get_provider(name: str | None = None) -> Provider:
    name = (name or DEFAULT_PROVIDER).lower()
    if name not in PROVIDERS:
        raise HTTPException(400, f"Unknown LLM provider '{name}'. Choose one of: {', '.join(PROVIDERS)}")
    if name not in _cache:
        _cache[name] = {"gemini": Gemini, "anthropic": Anthropic, "qwen_finetuned": QwenFinetuned}.get(name, lambda: OpenAICompatible(name))()
    return _cache[name]


def generate(prompt: str, system: str | None = None, max_tokens: int = 512, provider: str | None = None) -> str:
    p = get_provider(provider)
    try:
        return p.generate(prompt, system, max_tokens)
    except HTTPException:
        raise
    except Exception as e:  # network, quota, bad key, API not enabled
        raise HTTPException(502, f"LLM request failed ({p.name}): {type(e).__name__}") from e
