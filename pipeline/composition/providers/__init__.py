"""LLM backends for composition (text in → text out)."""

from __future__ import annotations

from typing import Protocol


class TextProvider(Protocol):
    """Model or stub that returns raw assistant text (ideally JSON only)."""

    def generate(self, messages: list[dict[str, str]]) -> str:
        ...
