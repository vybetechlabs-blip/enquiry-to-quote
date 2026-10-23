"""LLM provider factory: scripted / ollama / anthropic behind one interface.

Nothing here runs unless `--llm` mode is chosen (Phase 1). The scripted provider makes tests
deterministic; Ollama is used only if it is already running locally; Anthropic needs a key in
the environment and an explicit model id from the owner (no default model is assumed).
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Iterable
from typing import Protocol


class LLMProvider(Protocol):
    name: str

    def complete(self, system: str, prompt: str) -> str: ...


class ProviderUnavailable(RuntimeError):
    pass


class ScriptedLLM:
    """Returns canned responses in order. For tests and offline demos."""

    name = "scripted"

    def __init__(self, responses: Iterable[str]):
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if not self._responses:
            raise ProviderUnavailable("ScriptedLLM has no responses left")
        return self._responses.pop(0)


class OllamaLLM:
    """Local Ollama over HTTP. Uses 127.0.0.1: `localhost` adds IPv6 fallback delay on Windows."""

    name = "ollama"

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434", timeout: float = 120):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, prompt: str) -> str:
        payload = {"model": self.model, "system": system, "prompt": prompt, "stream": False}
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())["response"]
        except OSError as exc:
            raise ProviderUnavailable(f"Ollama not reachable at {self.host}: {exc}") from exc


class AnthropicLLM:
    """Anthropic Messages API. Needs ANTHROPIC_API_KEY and an explicit model id."""

    name = "anthropic"

    def __init__(self, model: str, max_tokens: int = 1024):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderUnavailable("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderUnavailable("install the extra: uv sync --extra llm") from exc
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    def complete(self, system: str, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")


def make_provider(name: str, *, model: str | None = None, **kwargs) -> LLMProvider:
    if name == "scripted":
        return ScriptedLLM(kwargs.get("responses", []))
    if not model:
        raise ProviderUnavailable(f"provider {name!r} needs an explicit model id")
    if name == "ollama":
        return OllamaLLM(model, **kwargs)
    if name == "anthropic":
        return AnthropicLLM(model, **kwargs)
    raise ValueError(f"unknown provider: {name}")
