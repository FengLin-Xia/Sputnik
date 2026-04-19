"""Run pipeline stages: seed → drift → composition → render → broadcast_package."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _cmd_render(args: argparse.Namespace) -> None:
    from pipeline.render.exporter import render_file_to_wav

    repo = Path(args.repo).resolve()
    score = (args.score if args.score.is_absolute() else repo / args.score).resolve()
    out = (args.out if args.out.is_absolute() else repo / args.out).resolve()
    render_file_to_wav(score, out, sample_rate=args.sr, seed=args.seed)
    print(f"Wrote {out}")


def _cmd_package(args: argparse.Namespace) -> None:
    from pipeline.broadcast_package.__main__ import main as package_main

    argv: list[str] = []
    if args.repo is not None:
        argv += ["--repo", str(args.repo)]
    if args.score is not None:
        argv += ["--score", str(args.score)]
    if args.audio is not None:
        argv += ["--audio", str(args.audio)]
    if args.out is not None:
        argv += ["--out", str(args.out)]
    if args.launch_at is not None:
        argv += ["--launch-at", args.launch_at]
    if args.orbit_day is not None:
        argv += ["--orbit-day", str(args.orbit_day)]
    package_main(argv)


def _cmd_compose(args: argparse.Namespace) -> None:
    from pipeline.composition.composer import compose, write_score_json
    from pipeline.composition.prompt_builder import CompositionInput
    from pipeline.composition.providers.mock_provider import MockProvider
    from pipeline.composition.providers.ollama_provider import OllamaProvider

    repo = Path(args.repo).resolve()
    seeds = tuple(args.seeds) if args.seeds else CompositionInput().seeds
    inp = CompositionInput(
        seeds=seeds,
        mode=args.mode,
        mood=args.mood,
        signal=args.signal,
    )
    if args.provider == "mock":
        provider = MockProvider()
    else:
        provider = OllamaProvider(
            model=args.model,
            base_url=args.ollama_url,
            timeout=args.timeout,
        )
    out_path = args.out if args.out.is_absolute() else repo / args.out
    result = compose(inp, provider, max_retries=args.max_retries)
    write_score_json(result.score, out_path)
    print(f"Wrote {out_path.resolve()} (attempts={result.attempts})")


def _cmd_all(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    score = (args.score if args.score.is_absolute() else repo / args.score).resolve()
    audio = (args.audio if args.audio.is_absolute() else repo / args.audio).resolve()
    _cmd_render(
        argparse.Namespace(
            repo=repo,
            score=score,
            out=audio,
            sr=args.sr,
            seed=args.seed,
        )
    )
    pkg_argv: list[str] = ["--repo", str(repo), "--score", str(score), "--audio", str(audio)]
    if args.out is not None:
        o = args.out if args.out.is_absolute() else repo / args.out
        pkg_argv += ["--out", str(o)]
    if args.launch_at is not None:
        pkg_argv += ["--launch-at", args.launch_at]
    if args.orbit_day is not None:
        pkg_argv += ["--orbit-day", str(args.orbit_day)]
    from pipeline.broadcast_package.__main__ import main as package_main

    package_main(pkg_argv)


def main() -> None:
    repo = _repo_root()
    ap = argparse.ArgumentParser(description="Sputnik offline pipeline")
    sub = ap.add_subparsers(dest="command", required=True)

    r = sub.add_parser("render", help="Score JSON → WAV (decoupled from package)")
    r.add_argument("--repo", type=Path, default=repo, help="Repository root")
    r.add_argument(
        "--score",
        type=Path,
        default=Path("pipeline/render/demo_score.json"),
        help="Input score JSON",
    )
    r.add_argument(
        "--out",
        type=Path,
        default=Path("broadcast/audio/rendered.wav"),
        help="Output WAV path",
    )
    r.add_argument("--sr", type=int, default=44100)
    r.add_argument("--seed", type=int, default=42)
    r.set_defaults(func=_cmd_render)

    c = sub.add_parser("compose", help="Composition v0.1 — score.json (mock or Ollama)")
    c.add_argument("--repo", type=Path, default=repo)
    c.add_argument("--provider", choices=("mock", "ollama"), default="mock")
    c.add_argument("--model", default="qwen2.5:7b")
    c.add_argument("--ollama-url", default=os.environ.get("OLLAMA_BASE_URL"))
    c.add_argument("--timeout", type=float, default=120.0)
    c.add_argument(
        "--out",
        type=Path,
        default=Path("composition_output/score.json"),
        help="Output score JSON",
    )
    c.add_argument("--seed", action="append", dest="seeds")
    c.add_argument("--mode", default="beacon")
    c.add_argument("--mood", default="cold")
    c.add_argument("--signal", default="stable")
    c.add_argument("--max-retries", type=int, default=3)
    c.set_defaults(func=_cmd_compose)

    p = sub.add_parser("package", help="Assemble broadcast/latest (see also: python -m pipeline.broadcast_package)")
    p.add_argument("--repo", type=Path, default=None)
    p.add_argument("--score", type=Path, default=None)
    p.add_argument("--audio", type=Path, default=None)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--launch-at", default=None)
    p.add_argument("--orbit-day", type=int, default=None)
    p.set_defaults(func=_cmd_package)

    a = sub.add_parser("all", help="Render then package (writes WAV then broadcast/latest/)")
    a.add_argument("--repo", type=Path, default=repo)
    a.add_argument("--score", type=Path, default=Path("pipeline/render/demo_score.json"))
    a.add_argument("--audio", type=Path, default=Path("broadcast/audio/rendered.wav"))
    a.add_argument("--out", type=Path, default=Path("broadcast/latest"))
    a.add_argument("--launch-at", default=None)
    a.add_argument("--orbit-day", type=int, default=None)
    a.add_argument("--sr", type=int, default=44100)
    a.add_argument("--seed", type=int, default=42)
    a.set_defaults(func=_cmd_all)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
