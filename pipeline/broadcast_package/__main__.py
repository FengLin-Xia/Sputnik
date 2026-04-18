"""CLI: assemble broadcast/latest (run from repo root: python -m pipeline.broadcast_package)."""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.broadcast_package.builder import (
    PackageInputs,
    build_package,
    default_fragments,
    default_meta,
    default_state,
)
from pipeline.broadcast_package.schema import (
    BroadcastMeta,
    BroadcastState,
    meta_to_jsonable,
    read_json,
    validate_fragments,
    validate_meta,
    validate_state,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(repo: Path, p: Path) -> Path:
    return p if p.is_absolute() else (repo / p).resolve()


def _parse_state(path: Path | None) -> BroadcastState:
    if path is None:
        return default_state()
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("state file must be a JSON object")
    return validate_state(data)


def _parse_fragments(path: Path | None) -> list[str]:
    if path is None:
        return list(default_fragments())
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("fragments file must be a JSON object")
    return validate_fragments(data)


def _parse_meta(path: Path | None, *, launch_at: str, orbit_day: int) -> BroadcastMeta:
    base = default_meta(launch_at=launch_at, orbit_day=orbit_day)
    if path is None:
        return base
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("meta file must be a JSON object")
    defaults = meta_to_jsonable(base)
    merged = {**defaults, **data}
    return validate_meta(merged)


def main(argv: list[str] | None = None) -> Path:
    root = _repo_root()
    ap = argparse.ArgumentParser(description="Build Broadcast Package v0.1 into broadcast/latest/")
    ap.add_argument(
        "--repo",
        type=Path,
        default=root,
        help="Repository root (default: inferred from package location)",
    )
    ap.add_argument(
        "--score",
        type=Path,
        default=Path("pipeline/render/demo_score.json"),
        help="Source score JSON (default: pipeline/render/demo_score.json)",
    )
    ap.add_argument(
        "--audio",
        type=Path,
        default=Path("broadcast/audio/rendered.wav"),
        help="Rendered WAV (default: broadcast/audio/rendered.wav)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("broadcast/latest"),
        help="Output directory (default: broadcast/latest)",
    )
    ap.add_argument(
        "--launch-at",
        default="2026-04-18T00:00:00Z",
        help="meta.launchAt ISO timestamp (default: 2026-04-18T00:00:00Z)",
    )
    ap.add_argument(
        "--orbit-day",
        type=int,
        default=1,
        help="meta.orbitDay (default: 1)",
    )
    ap.add_argument(
        "--state-json",
        type=Path,
        default=None,
        help="Optional state.json to merge shape (must include signal, mode, mood, transmission)",
    )
    ap.add_argument(
        "--fragments-json",
        type=Path,
        default=None,
        help="Optional fragments.json (fragments array)",
    )
    ap.add_argument(
        "--meta-json",
        type=Path,
        default=None,
        help="Optional meta.json (launchAt/orbitDay overridden by file when present)",
    )
    ap.add_argument(
        "--segment-id",
        default="segment_001",
        help="Segment id and base name for audio/segment.wav (default: segment_001)",
    )
    args = ap.parse_args(argv)

    repo = args.repo.resolve()
    score = _resolve(repo, args.score)
    audio = _resolve(repo, args.audio)
    out = _resolve(repo, args.out)

    state = _parse_state(args.state_json)
    fragments = _parse_fragments(args.fragments_json)
    meta = _parse_meta(args.meta_json, launch_at=args.launch_at, orbit_day=args.orbit_day)

    inp = PackageInputs(
        score_path=score,
        audio_wav_path=audio,
        out_dir=out,
        state=state,
        fragments=fragments,
        meta=meta,
        segment_id=args.segment_id,
    )
    path = build_package(inp)
    print(f"Wrote broadcast package: {path}")
    return path


if __name__ == "__main__":
    main()
