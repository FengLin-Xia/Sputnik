"""
Daily broadcast package v0.1: score, playlist, audio, fragments, state, meta —
static bundle for the frontend receiver.
"""

from pipeline.broadcast_package.builder import (
    PackageInputs,
    build_package,
    build_playlist,
    default_fragments,
    default_meta,
    default_state,
)

__all__ = [
    "PackageInputs",
    "build_package",
    "build_playlist",
    "default_fragments",
    "default_meta",
    "default_state",
]
