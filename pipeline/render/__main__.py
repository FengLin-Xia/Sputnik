"""CLI: render a score JSON to WAV (run from repo root: python -m pipeline.render)."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.render.exporter import render_file_to_wav


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Sputnik Render v0.1 — score.json → WAV")
    ap.add_argument(
        "--score",
        type=Path,
        default=here / "demo_score.json",
        help="Path to score JSON (default: pipeline/render/demo_score.json)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("rendered.wav"),
        help="Output WAV path (default: ./rendered.wav)",
    )
    ap.add_argument("--sr", type=int, default=44100, help="Sample rate (default 44100)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for static/ghost layer")
    args = ap.parse_args()
    render_file_to_wav(args.score, args.out, sample_rate=args.sr, seed=args.seed)
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
