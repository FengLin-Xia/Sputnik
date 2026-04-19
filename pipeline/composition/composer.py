"""Orchestrate prompt → provider → JSON extract → schema validation (with retries)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pipeline.render.schema import Score, score_from_dict

from pipeline.composition.prompt_builder import CompositionInput, build_messages
from pipeline.composition.providers import TextProvider


@dataclass
class ComposeResult:
    score: Score
    raw_text: str
    attempts: int


class ComposeError(Exception):
    """Raised when no attempt produced a valid score."""


def _strip_markdown_fences(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", t, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


def _first_json_object(s: str) -> str | None:
    """Extract first top-level JSON object by brace matching (handles trailing junk)."""

    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def parse_score_json(text: str) -> dict[str, Any]:
    """Parse model output into a dict suitable for score_from_dict."""

    cleaned = _strip_markdown_fences(text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        blob = _first_json_object(cleaned)
        if blob is None:
            raise ValueError("No JSON object found in model output") from None
        data = json.loads(blob)
    if not isinstance(data, dict):
        raise ValueError("Score root must be a JSON object")
    return data


def compose(
    inp: CompositionInput,
    provider: TextProvider,
    *,
    max_retries: int = 3,
) -> ComposeResult:
    """Build prompt, call provider, parse JSON, validate; retry on failure."""

    messages = build_messages(inp)
    last_err: Exception | None = None
    last_raw = ""
    for attempt in range(1, max_retries + 1):
        try:
            last_raw = provider.generate(messages)
            data = parse_score_json(last_raw)
            score = score_from_dict(data)
            return ComposeResult(score=score, raw_text=last_raw, attempts=attempt)
        except Exception as e:
            last_err = e
            continue
    raise ComposeError(
        f"Failed after {max_retries} attempt(s): {last_err}"
    ) from last_err


def score_to_json_dict(score: Score) -> dict[str, Any]:
    return {
        "bpm": score.bpm,
        "bars": score.bars,
        "notes": [asdict(n) for n in score.notes],
    }


def write_score_json(score: Score, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = score_to_json_dict(score)
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return p
