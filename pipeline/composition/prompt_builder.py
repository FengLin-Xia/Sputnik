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
    lyrics_text: str | None = None
    melody_mode: str = "beacon"
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
Do not add explanations, reasoning, markdown, code fences, or comments — only the raw JSON object.
/no_think"""

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
    if inp.lyrics_text:
        lyrics = inp.lyrics_text.strip()
        if len(lyrics) > 3000:
            lyrics = lyrics[:3000].rstrip() + "\n[truncated]"
        lines.extend(
            [
                "Lyric source material:",
                lyrics,
                "",
                "Use the lyric source only as emotional, rhythmic, and contour guidance.",
                "Do not quote, paraphrase, or output any lyric text.",
                "Translate the source into sparse note events only.",
            ]
        )
    if inp.melody_mode == "beacon":
        lines.extend(
            [
                "Melody requirements:",
                "- Output a compact score: 10-16 notes total.",
                "- Track 0 is the beacon melody and must carry a recognizable 4-7 note motif.",
                "- Repeat or echo that motif at least once with small variation.",
                "- Track 0 must use at least 4 notes, at least 3 distinct pitches, and a pitch span of 5-12 semitones.",
                "- Keep track 0 mostly in a singable register, roughly pitch 55-74.",
                "- Use tracks 1, 2, and 3 as sparse support only; do not let texture crowd the melody.",
                "- Prefer simple stepwise motion with a few small leaps; avoid random isolated events.",
            ]
        )
    if inp.extra_context:
        lines.append(f"Extra keys (reserved for future drift): {inp.extra_context!r}")

    user = "\n".join(lines) + "\n\nOutput the score JSON only."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
