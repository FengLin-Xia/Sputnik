"""
Composition v0.1: prompt → local LLM (Ollama) or mock → validated score.json.
"""

from pipeline.composition.composer import (
    ComposeError,
    ComposeResult,
    compose,
    parse_score_json,
    write_score_json,
)
from pipeline.composition.prompt_builder import CompositionInput, build_messages

__all__ = [
    "ComposeError",
    "ComposeResult",
    "CompositionInput",
    "build_messages",
    "compose",
    "parse_score_json",
    "write_score_json",
]
