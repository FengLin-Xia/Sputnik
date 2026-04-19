"""Build chat messages for local LLM: system constraints + seed + optional state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pipeline.render.schema import (
    BARS_ALLOWED,
    BPM_MAX,
    BPM_MIN,
    DURATION_MAX,
    DURATION_MIN,
    MAX_NOTES,
    PITCH_MAX,
    PITCH_MIN,
)


@dataclass(frozen=True)
class CompositionInput:
    """v0.1 minimal input: style seeds + optional broadcast state (drift hooks later)."""

    seeds: tuple[str, ...] = (
        "冷电子广播",
        "半导体",
        "低功率",
        "稀疏",
        "失败的歌唱",
    )
    mode: str | None = "beacon"
    mood: str | None = "cold"
    signal: str | None = "stable"
    extra_context: dict[str, Any] = field(default_factory=dict)


def _spec_block() -> str:
    return f"""Score JSON must match Sputnik score spec v0.1 exactly:
- Top level: bpm (number), bars (integer), notes (array).
- bars must be one of {BARS_ALLOWED}.
- bpm must be between {BPM_MIN} and {BPM_MAX} inclusive.
- notes: at most {MAX_NOTES} objects.
- Each note: t, d, p, v, track (exact keys).
  - t: start time in beats from segment start (>= 0).
  - d: duration in beats, between {DURATION_MIN} and {DURATION_MAX}.
  - p: MIDI pitch, integer between {PITCH_MIN} and {PITCH_MAX}.
  - v: velocity, number in (0, 1].
  - track: integer 0–3 only (0 beacon, 1 drone, 2 static/ghost, 3 relay/ping).
- Every note must satisfy t + d <= bars * 4 beats (segment length).
"""


def build_messages(inp: CompositionInput) -> list[dict[str, str]]:
    """Return Ollama-style chat messages: system + user."""

    system = f"""You are the composition engine for Sputnik, a sparse cold broadcast signal.
Your only job is to output ONE valid JSON object — the musical score — and nothing else.

{_spec_block()}

Aesthetic (light touch): sparse, cold, mechanical, broadcast-like; not a pop song; more like failed singing.
Do not add explanations, markdown, code fences, or comments — only the raw JSON object."""

    lines = [
        "Style seeds (hints):",
        *[f"- {s}" for s in inp.seeds],
    ]
    if inp.mode or inp.mood or inp.signal:
        lines.append("Current state (optional context):")
        if inp.mode:
            lines.append(f"- mode: {inp.mode}")
        if inp.mood:
            lines.append(f"- mood: {inp.mood}")
        if inp.signal:
            lines.append(f"- signal: {inp.signal}")
    if inp.extra_context:
        lines.append(f"Extra keys (reserved for future drift): {inp.extra_context!r}")

    user = "\n".join(lines) + "\n\nOutput the score JSON only."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
