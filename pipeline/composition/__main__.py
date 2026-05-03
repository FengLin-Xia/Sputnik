"""CLI: generate score.json via mock or Ollama (run from repo root: python -m pipeline.composition)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pipeline.composition.composer import compose, write_score_json
from pipeline.composition.prompt_builder import CompositionInput
from pipeline.composition.providers import TextProvider
from pipeline.composition.providers.deepseek_provider import DeepSeekProvider
from pipeline.composition.providers.mock_provider import MockProvider
from pipeline.composition.providers.ollama_provider import OllamaProvider


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    repo = _repo_root()
    ap = argparse.ArgumentParser(description="Sputnik Composition v0.1 — score.json")
    ap.add_argument(
        "--provider",
        choices=("mock", "ollama", "deepseek"),
        default="mock",
        help="mock = no network; ollama = local /api/chat; deepseek = hosted API",
    )
    ap.add_argument("--model", default=None, help="Model tag/name for the selected provider")
    ap.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_BASE_URL"),
        help="Base URL (default: http://$OLLAMA_HOST or http://127.0.0.1:11434)",
    )
    ap.add_argument(
        "--deepseek-url",
        default=os.environ.get("DEEPSEEK_BASE_URL"),
        help="Base URL (default: https://api.deepseek.com)",
    )
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument(
        "--out",
        type=Path,
        default=repo / "composition_output" / "score.json",
        help="Output path (default: composition_output/score.json)",
    )
    ap.add_argument(
        "--seed",
        action="append",
        dest="seeds",
        help="Style seed (repeatable); defaults used if none",
    )
    ap.add_argument("--mode", default="beacon")
    ap.add_argument("--mood", default="cold")
    ap.add_argument("--signal", default="stable")
    ap.add_argument("--melody-mode", choices=("beacon", "off"), default="beacon")
    ap.add_argument(
        "--lyrics-file",
        type=Path,
        default=None,
        help="Optional lyric/text source file used as prompt context only",
    )
    ap.add_argument("--max-retries", type=int, default=3)
    args = ap.parse_args()

    seeds = tuple(args.seeds) if args.seeds else CompositionInput().seeds
    lyrics_text = args.lyrics_file.read_text(encoding="utf-8") if args.lyrics_file else None
    inp = CompositionInput(
        seeds=seeds,
        mode=args.mode,
        mood=args.mood,
        signal=args.signal,
        lyrics_text=lyrics_text,
        melody_mode=args.melody_mode,
    )

    provider: TextProvider
    if args.provider == "mock":
        provider = MockProvider()
    elif args.provider == "ollama":
        provider = OllamaProvider(
            model=args.model or "qwen2.5:7b",
            base_url=args.ollama_url,
            timeout=args.timeout,
        )
    else:
        provider = DeepSeekProvider(
            model=args.model,
            base_url=args.deepseek_url,
            timeout=args.timeout,
        )

    result = compose(inp, provider, max_retries=args.max_retries)
    out = write_score_json(result.score, args.out)
    print(f"Wrote {out.resolve()} (attempts={result.attempts})")


if __name__ == "__main__":
    main()
