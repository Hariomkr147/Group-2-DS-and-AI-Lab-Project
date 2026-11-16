"""LLM endpoints. The optional `provider` field in the body overrides LLM_PROVIDER."""
import json
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services import llm

router = APIRouter(tags=["llm"])


class LLMRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    system: str | None = Field(None, max_length=2000)
    max_tokens: int = Field(512, ge=1, le=2048)
    # Optional. Omit to use LLM_PROVIDER from the env (default gemini).
    provider: Literal["gemini", "openai", "anthropic", "ollama", "qwen_finetuned"] | None = None


class LLMResponse(BaseModel):
    text: str
    provider: str
    model: str


@router.post("/llm/generate", response_model=LLMResponse)
def generate(body: LLMRequest):
    """Send a prompt to the LLM and return its reply (bearer token required)."""
    p = llm.get_provider(body.provider)
    text = llm.generate(body.prompt, body.system, body.max_tokens, body.provider)
    return LLMResponse(text=text, provider=p.name, model=p.model)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/llm/stream")
def stream(body: LLMRequest):
    """Same as /llm/generate but streams the reply as server-sent events:
    `chunk` events with {"text": ...}, then one `done` event (or `error` if it fails midway)."""
    p = llm.get_provider(body.provider)
    p.ready()  # real 400/503 now, before the 200 is sent

    def events():
        try:
            for text in p.stream(body.prompt, body.system, body.max_tokens):
                yield _sse("chunk", {"text": text})
            yield _sse("done", {"provider": p.name, "model": p.model})
        except Exception as e:
            yield _sse("error", {"detail": f"LLM stream failed ({p.name}): {type(e).__name__}"})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
