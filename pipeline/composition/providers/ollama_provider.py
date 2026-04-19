"""Call local Ollama HTTP API (/api/chat); returns assistant message content only."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _default_base_url() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host}".rstrip("/")


class OllamaProvider:
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._model = model
        self._base = (base_url or _default_base_url()).rstrip("/")
        self._timeout = timeout

    def generate(self, messages: list[dict[str, str]]) -> str:
        url = f"{self._base}/api/chat"
        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection failed: {e}") from e

        payload = json.loads(raw)
        msg = payload.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return str(msg["content"])
        # /api/generate style fallback
        if isinstance(payload.get("response"), str):
            return str(payload["response"])
        raise RuntimeError(f"Unexpected Ollama response shape: {payload!r}")
