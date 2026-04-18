"""Broadcast Package v0.1 — minimal JSON shapes and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Sequence


PACKAGE_VERSION = "0.1.0"


@dataclass(frozen=True)
class BroadcastState:
    signal: str
    mode: str
    mood: str
    transmission: str


@dataclass(frozen=True)
class BroadcastMeta:
    launch_at: str
    generated_at: str
    orbit_day: int
    package_version: str
    audio_format: str


@dataclass(frozen=True)
class PlaylistSegment:
    id: str
    audio: str
    score: str
    start_offset: float


@dataclass(frozen=True)
class Playlist:
    segments: List[PlaylistSegment]


def _require_str(d: Mapping[str, Any], key: str, ctx: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{ctx}: {key!r} must be a non-empty string")
    return v


def _require_int(d: Mapping[str, Any], key: str, ctx: str) -> int:
    v = d.get(key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"{ctx}: {key!r} must be an int")
    return v


def _require_float(d: Mapping[str, Any], key: str, ctx: str) -> float:
    v = d.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"{ctx}: {key!r} must be a number")
    return float(v)


def validate_state(data: Mapping[str, Any]) -> BroadcastState:
    ctx = "state.json"
    return BroadcastState(
        signal=_require_str(data, "signal", ctx),
        mode=_require_str(data, "mode", ctx),
        mood=_require_str(data, "mood", ctx),
        transmission=_require_str(data, "transmission", ctx),
    )


def validate_meta(data: Mapping[str, Any]) -> BroadcastMeta:
    ctx = "meta.json"
    od = _require_int(data, "orbitDay", ctx)
    if od < 1:
        raise ValueError(f"{ctx}: orbitDay must be >= 1")
    return BroadcastMeta(
        launch_at=_require_str(data, "launchAt", ctx),
        generated_at=_require_str(data, "generatedAt", ctx),
        orbit_day=od,
        package_version=_require_str(data, "packageVersion", ctx),
        audio_format=_require_str(data, "audioFormat", ctx),
    )


def validate_playlist(data: Mapping[str, Any]) -> Playlist:
    ctx = "playlist.json"
    raw = data.get("segments")
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{ctx}: segments must be a non-empty list")
    segments: List[PlaylistSegment] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise TypeError(f"{ctx}: segments[{i}] must be an object")
        seg_ctx = f"{ctx} segments[{i}]"
        segments.append(
            PlaylistSegment(
                id=_require_str(item, "id", seg_ctx),
                audio=_require_str(item, "audio", seg_ctx),
                score=_require_str(item, "score", seg_ctx),
                start_offset=_require_float(item, "startOffset", seg_ctx),
            )
        )
    return Playlist(segments=segments)


def validate_fragments(data: Mapping[str, Any]) -> List[str]:
    ctx = "fragments.json"
    raw = data.get("fragments")
    if not isinstance(raw, list):
        raise ValueError(f"{ctx}: fragments must be a list")
    out: List[str] = []
    for i, x in enumerate(raw):
        if not isinstance(x, str):
            raise TypeError(f"{ctx}: fragments[{i}] must be a string")
        out.append(x)
    return out


def state_to_jsonable(state: BroadcastState) -> dict[str, Any]:
    return {
        "signal": state.signal,
        "mode": state.mode,
        "mood": state.mood,
        "transmission": state.transmission,
    }


def meta_to_jsonable(meta: BroadcastMeta) -> dict[str, Any]:
    return {
        "launchAt": meta.launch_at,
        "generatedAt": meta.generated_at,
        "orbitDay": meta.orbit_day,
        "packageVersion": meta.package_version,
        "audioFormat": meta.audio_format,
    }


def playlist_to_jsonable(pl: Playlist) -> dict[str, Any]:
    return {
        "segments": [
            {
                "id": s.id,
                "audio": s.audio,
                "score": s.score,
                "startOffset": s.start_offset,
            }
            for s in pl.segments
        ]
    }


def fragments_to_jsonable(lines: Sequence[str]) -> dict[str, Any]:
    return {"fragments": list(lines)}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
