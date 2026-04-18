"""Sputnik Score v0.1 — validation and loading (see Sputnik_Score_Spec_PrV01.md)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List


BEATS_PER_BAR = 4

# Hard / recommended bounds aligned with the published spec
BPM_MIN = 50
BPM_MAX = 100
BARS_ALLOWED = (4, 8)
PITCH_MIN = 48
PITCH_MAX = 84
DURATION_MIN = 0.25
DURATION_MAX = 4.0
MAX_NOTES = 64


@dataclass(frozen=True)
class Note:
    """One note on the fixed beat grid."""

    t: float  # start (beats from score start)
    d: float  # duration (beats)
    p: int  # MIDI-style pitch
    v: float  # velocity 0..1
    track: int  # 0 beacon, 1 drone, 2 static/ghost, 3 relay/ping


@dataclass(frozen=True)
class Score:
    bpm: float
    bars: int
    notes: List[Note]

    @property
    def total_beats(self) -> float:
        return float(self.bars * BEATS_PER_BAR)


def _as_float(x: Any, field: str) -> float:
    if isinstance(x, (int, float)):
        return float(x)
    raise TypeError(f"{field} must be a number, got {type(x).__name__}")


def _note_from_dict(raw: dict[str, Any], index: int) -> Note:
    try:
        t = _as_float(raw["t"], "t")
        d = _as_float(raw["d"], "d")
        p = int(raw["p"])
        v = _as_float(raw["v"], "v")
        tr = int(raw["track"])
    except KeyError as e:
        raise ValueError(f"notes[{index}]: missing field {e.args[0]}") from e
    except (TypeError, ValueError) as e:
        raise ValueError(f"notes[{index}]: invalid field types: {e}") from e
    return Note(t=t, d=d, p=p, v=v, track=tr)


def validate_score(score: Score) -> None:
    if not (BPM_MIN <= score.bpm <= BPM_MAX):
        raise ValueError(f"bpm must be in [{BPM_MIN}, {BPM_MAX}] (v0.1 spec)")
    if score.bars not in BARS_ALLOWED:
        raise ValueError(f"bars must be one of {BARS_ALLOWED} (v0.1 spec)")
    if len(score.notes) > MAX_NOTES:
        raise ValueError(f"notes: at most {MAX_NOTES} notes in v0.1")
    total = score.total_beats
    for i, n in enumerate(score.notes):
        if n.t < 0:
            raise ValueError(f"notes[{i}]: t must be >= 0")
        if not (DURATION_MIN <= n.d <= DURATION_MAX):
            raise ValueError(
                f"notes[{i}]: d must be in [{DURATION_MIN}, {DURATION_MAX}] (grid units, v0.1)"
            )
        if n.t + n.d > total + 1e-9:
            raise ValueError(f"notes[{i}]: t+d exceeds segment ({n.t}+{n.d} > {total} beats)")
        if not (PITCH_MIN <= n.p <= PITCH_MAX):
            raise ValueError(f"notes[{i}]: p must be in [{PITCH_MIN}, {PITCH_MAX}] (v0.1)")
        if not (0.0 < n.v <= 1.0):
            raise ValueError(f"notes[{i}]: v must be in (0, 1] (v0.1)")
        if n.track < 0 or n.track > 3:
            raise ValueError(f"notes[{i}]: track must be 0–3 in v0.1")


def load_score(path: str | Path) -> Score:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("score root must be a JSON object")
    bpm = _as_float(data["bpm"], "bpm")
    bars = int(data["bars"])
    raw_notes = data["notes"]
    if not isinstance(raw_notes, list):
        raise ValueError("notes must be a list")
    notes: List[Note] = []
    for i, x in enumerate(raw_notes):
        if not isinstance(x, dict):
            raise ValueError(f"notes[{i}] must be an object")
        notes.append(_note_from_dict(x, i))
    score = Score(bpm=bpm, bars=bars, notes=notes)
    validate_score(score)
    return score


def score_from_dict(data: dict[str, Any]) -> Score:
    """Parse an already-loaded dict (tests / embedding)."""

    bpm = _as_float(data["bpm"], "bpm")
    bars = int(data["bars"])
    raw_notes = data["notes"]
    if not isinstance(raw_notes, list):
        raise ValueError("notes must be a list")
    notes: List[Note] = []
    for i, x in enumerate(raw_notes):
        if not isinstance(x, dict):
            raise ValueError(f"notes[{i}] must be an object")
        notes.append(_note_from_dict(x, i))
    score = Score(bpm=bpm, bars=bars, notes=notes)
    validate_score(score)
    return score
