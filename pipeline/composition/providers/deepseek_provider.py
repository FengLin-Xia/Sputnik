"""Call DeepSeek's OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _load_dotenv(path: str | Path = ".env") -> None:
    """Tiny .env loader for local CLI use; real environment variables win."""

    p = Path(path)
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _default_base_url() -> str:
    return os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


class DeepSeekProvider:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
        temperature: float = 0.25,
        max_tokens: int = 1600,
    ) -> None:
        _load_dotenv()
        self._model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
        self._base = (base_url or _default_base_url()).rstrip("/")
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self._timeout = timeout
        self._temperature = temperature
        self._max_tokens = max_tokens
        if not self._api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for --provider deepseek")

    def generate(self, messages: list[dict[str, str]]) -> str:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            _chat_url(self._base),
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"DeepSeek connection failed: {e}") from e

        payload = json.loads(raw)
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return str(msg["content"])
        raise RuntimeError(f"Unexpected DeepSeek response shape: {payload!r}")

