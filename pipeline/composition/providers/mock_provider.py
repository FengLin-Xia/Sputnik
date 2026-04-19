"""Deterministic fake model output for CI and package wiring without Ollama."""

from __future__ import annotations

# Valid v0.1 score (same shape as pipeline/render/demo_score.json) — no network required.
_MOCK_SCORE_JSON = """{
  "bpm": 72,
  "bars": 4,
  "notes": [
    { "t": 0, "d": 1, "p": 60, "v": 0.8, "track": 0 },
    { "t": 2, "d": 1, "p": 64, "v": 0.6, "track": 1 },
    { "t": 4, "d": 2, "p": 67, "v": 0.5, "track": 0 },
    { "t": 6, "d": 0.5, "p": 72, "v": 0.45, "track": 0 },
    { "t": 7, "d": 1, "p": 55, "v": 0.35, "track": 1 },
    { "t": 8, "d": 0.25, "p": 84, "v": 0.4, "track": 2 },
    { "t": 9, "d": 0.35, "p": 79, "v": 0.42, "track": 3 },
    { "t": 10, "d": 0.25, "p": 83, "v": 0.35, "track": 2 },
    { "t": 11, "d": 0.4, "p": 76, "v": 0.38, "track": 3 },
    { "t": 12, "d": 1.5, "p": 64, "v": 0.55, "track": 0 }
  ]
}"""


class MockProvider:
    def generate(self, messages: list[dict[str, str]]) -> str:
        _ = messages
        return _MOCK_SCORE_JSON
