"""
OpenRouter AI Client with Fallback Chain
Prevents circular recursion and token exhaustion.
"""
import asyncio
import time
from typing import AsyncGenerator, Optional
import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from backend.config import settings

log = structlog.get_logger()

# ──────────────────────────────────────────────
# Fallback model chain (free tier only)
# ──────────────────────────────────────────────
FALLBACK_CHAIN = [
    "nvidia/nemotron-3-nano-30b-a3b:free",         # Primary: Successfully generated without 429
    "google/gemini-2.0-flash-exp:free",            # Fallback 1: High capacity
    "openai/gpt-oss-120b:free",                    # Fallback 2: OSS Heavy
    "deepseek/deepseek-v4-flash:free",             # Fallback 3: Tends to 429, kept as backup
]

# Per-agent model assignments (all using verified active free models)
AGENT_MODELS = {
    "orchestrator":   "nvidia/nemotron-3-nano-30b-a3b:free",
    "planner":        "nvidia/nemotron-3-nano-30b-a3b:free",
    "layout":         "nvidia/nemotron-3-nano-30b-a3b:free",
    "geometry":       "nvidia/nemotron-3-nano-30b-a3b:free",
    "asset":          "nvidia/nemotron-3-nano-30b-a3b:free",
    "visualization":  "nvidia/nemotron-3-nano-30b-a3b:free",
    "compliance":     "nvidia/nemotron-3-nano-30b-a3b:free",
    "bull":           "nvidia/nemotron-3-nano-30b-a3b:free",
    "bear":           "nvidia/nemotron-3-nano-30b-a3b:free",
    "skeptic":        "nvidia/nemotron-3-nano-30b-a3b:free",
}

# Circuit breaker state: model_id -> failure_count
_circuit_breaker: dict[str, int] = {}
CIRCUIT_BREAKER_THRESHOLD = 3

# Anti-recursion: tracks active agent calls
_active_agents: set[str] = set()
MAX_AGENT_TOKENS = 2048
MAX_RETRIES = 3


def _is_circuit_open(model: str) -> bool:
    return _circuit_breaker.get(model, 0) >= CIRCUIT_BREAKER_THRESHOLD


def _record_failure(model: str) -> None:
    _circuit_breaker[model] = _circuit_breaker.get(model, 0) + 1
    log.warning("model_failure", model=model, failures=_circuit_breaker[model])


def _record_success(model: str) -> None:
    _circuit_breaker[model] = 0


def get_fallback_chain(preferred_model: str) -> list[str]:
    """Return ordered fallback list starting from preferred model."""
    chain = [preferred_model] if preferred_model not in FALLBACK_CHAIN else []
    chain += [m for m in FALLBACK_CHAIN if m != preferred_model]
    return chain


class OpenRouterClient:
    """
    Async OpenRouter client with:
    - Model fallback chain
    - Circuit breaker per model
    - Anti-circular-recursion guard
    - Token budget enforcement
    """

    def __init__(self):
        self.base_url = settings.openrouter_base_url
        self.api_key = settings.openrouter_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://ai-architect.app",
            "X-Title": "AI Architect",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[dict],
        agent_id: str = "default",
        preferred_model: Optional[str] = None,
        max_tokens: int = MAX_AGENT_TOKENS,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str:
        """
        Send a chat completion request with automatic fallback.
        Raises RuntimeError if all models fail.
        """
        # ── Anti-recursion guard ──
        if agent_id in _active_agents:
            raise RuntimeError(
                f"Circular recursion detected: agent '{agent_id}' is already active."
            )
        _active_agents.add(agent_id)

        try:
            preferred = preferred_model or AGENT_MODELS.get(agent_id, FALLBACK_CHAIN[0])
            chain = get_fallback_chain(preferred)
            last_error = None

            for attempt, model in enumerate(chain):
                if _is_circuit_open(model):
                    log.info("circuit_open_skip", model=model)
                    continue

                try:
                    result = await self._call(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    _record_success(model)
                    log.info(
                        "llm_success",
                        agent=agent_id,
                        model=model,
                        attempt=attempt,
                    )
                    return result

                except (httpx.HTTPStatusError, httpx.TimeoutException, Exception) as e:
                    last_error = e
                    _record_failure(model)
                    log.warning(
                        "llm_fallback",
                        agent=agent_id,
                        model=model,
                        error=str(e),
                        next_model=chain[attempt + 1] if attempt + 1 < len(chain) else "none",
                    )
                    await asyncio.sleep(1)  # Brief pause before fallback

            raise RuntimeError(
                f"All models exhausted for agent '{agent_id}'. Last error: {last_error}"
            )

        finally:
            _active_agents.discard(agent_id)

    async def _call(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict],
        agent_id: str = "default",
        preferred_model: Optional[str] = None,
        max_tokens: int = MAX_AGENT_TOKENS,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat with fallback."""
        preferred = preferred_model or AGENT_MODELS.get(agent_id, FALLBACK_CHAIN[0])
        chain = get_fallback_chain(preferred)

        for model in chain:
            if _is_circuit_open(model):
                continue
            try:
                async for chunk in self._stream_call(model, messages, max_tokens):
                    yield chunk
                return
            except Exception as e:
                _record_failure(model)
                log.warning("stream_fallback", model=model, error=str(e))

    async def _stream_call(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except Exception:
                            pass


# Singleton
openrouter = OpenRouterClient()
