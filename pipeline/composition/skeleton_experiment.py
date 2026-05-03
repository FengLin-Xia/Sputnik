"""Experimental numbered skeleton -> degraded long-form WAV.

This is intentionally separate from score v0.1. The current public score schema
is a short 4/8-bar segment; this helper is for listening tests where we want a
longer melody-degradation sketch before deciding how to formalize playlists.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict
from pathlib import Path

from pipeline.render.effects import process_broadcast_chain
from pipeline.render.exporter import export_wav_mono
from pipeline.render.schema import Note, Score
from pipeline.render.synth import DEFAULT_SAMPLE_RATE, render_score


_MAJOR = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
_MINOR = {1: 0, 2: 2, 3: 3, 4: 5, 5: 7, 6: 8, 7: 10}


def _read_value(text: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _block_after_key(text: str, key: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    active = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            active = True
            rest = stripped.split("=", 1)[1].strip()
            if rest:
                out.append(rest)
            continue
        if active:
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", stripped) or stripped == "[RAW]":
                break
            if stripped and not stripped.startswith("#"):
                out.append(stripped)
    return " ".join(out)


def _tokens(s: str) -> list[str]:
    cleaned = s.replace("|", " ")
    return [t for t in cleaned.split() if t]


def _degree_to_pitch(token: str, key: int, scale: str) -> int | None:
    token = token.strip()
    if token in {"0", "-"}:
        return None

    accidental = 0
    while token.startswith("#") or token.startswith("b"):
        accidental += 1 if token[0] == "#" else -1
        token = token[1:]

    octave = 0
    while token.endswith(",") or token.endswith("'"):
        octave += -12 if token.endswith(",") else 12
        token = token[:-1]

    if not token.isdigit():
        return None
    degree = int(token)
    table = _MINOR if scale == "minor" else _MAJOR
    if degree not in table:
        return None
    return key + table[degree] + accidental + octave


def load_skeleton(path: str | Path) -> tuple[int, float, list[tuple[int | None, float]]]:
    text = Path(path).read_text(encoding="utf-8")
    key = int(_read_value(text, "key") or "60")
    bpm = float(_read_value(text, "bpm") or "70")
    scale = (_read_value(text, "scale") or "major").lower()

    degree_block = _block_after_key(text, "degrees")
    duration_block = _block_after_key(text, "durations")
    degree_tokens = _tokens(degree_block)
    duration_tokens = _tokens(duration_block)
    if not degree_tokens:
        raw = text.split("[RAW]", 1)[1] if "[RAW]" in text else text
        degree_tokens = [t for t in _tokens(raw) if not t.startswith("[")]

    pitches = [_degree_to_pitch(t, key, scale) for t in degree_tokens]
    durations: list[float] = []
    for i, token in enumerate(degree_tokens):
        if i < len(duration_tokens):
            try:
                durations.append(float(duration_tokens[i]))
                continue
            except ValueError:
                pass
        durations.append(1.0 if token == "-" else 0.5)
    return key, bpm, list(zip(pitches, durations))


def _clamp_pitch(p: int) -> int:
    return max(48, min(84, p))


def build_degraded_score(
    events: list[tuple[int | None, float]],
    *,
    bpm: float,
    target_seconds: float,
    seed: int = 7,
) -> Score:
    import numpy as np

    rng = np.random.default_rng(seed)
    target_beats = target_seconds * bpm / 60.0
    notes: list[Note] = []
    t = 0.0
    event_index = 0
    last_beacon_pitch = 62

    drone_roots = [50, 45, 48, 43]
    drone_t = 0.0
    drone_i = 0
    while drone_t < target_beats:
        progress = min(1.0, drone_t / max(1.0, target_beats))
        root = _clamp_pitch(drone_roots[drone_i % len(drone_roots)] + (1 if progress > 0.65 else 0))
        notes.append(Note(t=round(drone_t, 3), d=4.0, p=root, v=0.18 + 0.08 * progress, track=1))
        if drone_i % 2 == 1:
            notes.append(Note(t=round(drone_t + 2.0, 3), d=2.0, p=_clamp_pitch(root + 7), v=0.11, track=1))
        drone_t += 4.0
        drone_i += 1

    phrase_t = 0.0
    while phrase_t < target_beats:
        progress = min(1.0, phrase_t / max(1.0, target_beats))
        p = _clamp_pitch(67 - int(4 * progress))
        notes.append(Note(t=round(phrase_t + 3.5, 3), d=0.25, p=p, v=0.18 + 0.08 * progress, track=3))
        notes.append(Note(t=round(phrase_t + 7.5, 3), d=0.25, p=_clamp_pitch(p + 5), v=0.16, track=3))
        phrase_t += 8.0

    while t < target_beats:
        progress = min(1.0, t / max(1.0, target_beats))
        pitch, dur = events[event_index % len(events)]
        event_index += 1
        d = max(0.25, min(2.0, dur))

        if pitch is None:
            t += d
            continue

        drop_chance = 0.04 + 0.24 * progress
        ghost_chance = 0.08 + 0.18 * progress
        relay_chance = 0.06 + 0.16 * progress
        jitter = rng.choice([-2, -1, 0, 0, 0, 1, 2]) if progress > 0.25 else 0
        compressed = round((pitch - 62) * (1.0 - 0.35 * progress)) + 62
        p = _clamp_pitch(int(compressed + jitter))
        last_beacon_pitch = p
        v = max(0.16, 0.68 - 0.24 * progress + float(rng.normal(0.0, 0.04)))

        if rng.random() > drop_chance:
            notes.append(Note(t=round(t, 3), d=d, p=p, v=min(0.82, v), track=0))

        if rng.random() < ghost_chance:
            notes.append(Note(t=round(t + d * 0.5, 3), d=0.25, p=_clamp_pitch(p + 12), v=0.11, track=2))

        if rng.random() < relay_chance:
            notes.append(Note(t=round(t + d, 3), d=0.25, p=_clamp_pitch(p + 7), v=0.17, track=3))

        if int(t * 2) % 16 == 0 and progress > 0.2:
            notes.append(Note(t=round(t + 0.25, 3), d=0.25, p=_clamp_pitch(last_beacon_pitch - 5), v=0.09, track=2))

        t += d

    bars = int(math.ceil(target_beats / 4.0))
    total = bars * 4.0
    clipped = [n for n in notes if n.t + n.d <= total]
    return Score(bpm=bpm, bars=bars, notes=clipped)


def main() -> None:
    ap = argparse.ArgumentParser(description="Experimental numbered skeleton -> degraded WAV")
    ap.add_argument("--skeleton", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("composition_output/skeleton_degraded_2min.wav"))
    ap.add_argument("--score-out", type=Path, default=None)
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--sr", type=int, default=DEFAULT_SAMPLE_RATE)
    args = ap.parse_args()

    _key, bpm, events = load_skeleton(args.skeleton)
    score = build_degraded_score(events, bpm=bpm, target_seconds=args.seconds, seed=args.seed)
    if args.score_out is not None:
        args.score_out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "bpm": score.bpm,
            "bars": score.bars,
            "notes": [asdict(n) for n in score.notes],
        }
        args.score_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    dry = render_score(score, sample_rate=args.sr, seed=args.seed)
    import numpy as np

    wet = process_broadcast_chain(dry, args.sr, rng=np.random.default_rng(args.seed))
    export_wav_mono(wet, args.out, sample_rate=args.sr)
    print(f"Wrote {args.out.resolve()} ({args.seconds:.1f}s, bars={score.bars}, notes={len(score.notes)})")


if __name__ == "__main__":
    main()
