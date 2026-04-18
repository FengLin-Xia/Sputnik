"""Assemble broadcast/latest from score, WAV, state, fragments, and meta."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pipeline.render.schema import load_score

from pipeline.broadcast_package.schema import (
    BroadcastMeta,
    BroadcastState,
    PACKAGE_VERSION,
    Playlist,
    PlaylistSegment,
    fragments_to_jsonable,
    meta_to_jsonable,
    playlist_to_jsonable,
    read_json,
    state_to_jsonable,
    validate_fragments,
    validate_meta,
    validate_playlist,
    validate_state,
    write_json,
)


DEFAULT_SEGMENT_ID = "segment_001"
DEFAULT_SEGMENT_WAV = "audio/segment_001.wav"


@dataclass(frozen=True)
class PackageInputs:
    """Inputs for a single-segment v0.1 package."""

    score_path: Path
    audio_wav_path: Path
    out_dir: Path
    state: BroadcastState
    fragments: Sequence[str]
    meta: BroadcastMeta
    segment_id: str = DEFAULT_SEGMENT_ID


def _validate_score_for_render(score_path: Path) -> None:
    """Ensure the score is compatible with the render pipeline (same source of truth)."""

    load_score(score_path)


def build_playlist(segment_id: str = DEFAULT_SEGMENT_ID) -> Playlist:
    return Playlist(
        segments=[
            PlaylistSegment(
                id=segment_id,
                audio=DEFAULT_SEGMENT_WAV,
                score="score.json",
                start_offset=0.0,
            )
        ]
    )


def build_package(inp: PackageInputs) -> Path:
    """
    Write a full Broadcast Package v0.1 to ``inp.out_dir`` (e.g. broadcast/latest).

    Copies ``score_path`` and ``audio_wav_path`` into the package layout; writes
    state, meta, playlist, and fragments JSON.
    """

    _validate_score_for_render(inp.score_path)
    if not inp.audio_wav_path.is_file():
        raise FileNotFoundError(f"audio not found: {inp.audio_wav_path}")

    out = inp.out_dir
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(inp.score_path, out / "score.json")
    dest_wav = audio_dir / f"{inp.segment_id}.wav"
    shutil.copyfile(inp.audio_wav_path, dest_wav)

    pl = build_playlist(segment_id=inp.segment_id)
    write_json(out / "state.json", state_to_jsonable(inp.state))
    write_json(out / "meta.json", meta_to_jsonable(inp.meta))
    write_json(out / "playlist.json", playlist_to_jsonable(pl))
    write_json(out / "fragments.json", fragments_to_jsonable(inp.fragments))

    # Round-trip validate written JSON
    validate_state(read_json(out / "state.json"))
    validate_meta(read_json(out / "meta.json"))
    validate_playlist(read_json(out / "playlist.json"))
    validate_fragments(read_json(out / "fragments.json"))

    return out


def default_meta(
    *,
    launch_at: str,
    orbit_day: int,
    generated_at: datetime | None = None,
    audio_format: str = "wav",
) -> BroadcastMeta:
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    gen_iso = generated_at.isoformat().replace("+00:00", "Z")
    return BroadcastMeta(
        launch_at=launch_at,
        generated_at=gen_iso,
        orbit_day=orbit_day,
        package_version=PACKAGE_VERSION,
        audio_format=audio_format,
    )


def default_state() -> BroadcastState:
    return BroadcastState(
        signal="stable",
        mode="beacon",
        mood="cold",
        transmission="active",
    )


def default_fragments() -> list[str]:
    return [
        "still transmitting",
        "cold signal",
        "no confirmed return",
    ]
