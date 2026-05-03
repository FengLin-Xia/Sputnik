"""Composition-only melody sanity checks.

These checks are intentionally outside the core score schema. The render and
frontend only need valid score JSON; composition can be stricter when we want a
more singable beacon line from a local model.
"""

from __future__ import annotations

from pipeline.render.schema import Score


class MelodyValidationError(ValueError):
    """Raised when a valid score is too texture-like for melody-focused output."""


def validate_beacon_melody(score: Score) -> None:
    """Require track 0 to read as a sparse, repeatable melodic beacon."""

    beacon = sorted((n for n in score.notes if n.track == 0), key=lambda n: n.t)
    if len(beacon) < 4:
        raise MelodyValidationError(
            f"track 0 needs at least 4 beacon melody notes; got {len(beacon)}"
        )

    pitches = [n.p for n in beacon]
    unique_pitches = set(pitches)
    if len(unique_pitches) < 3:
        raise MelodyValidationError(
            f"track 0 needs at least 3 distinct pitches; got {len(unique_pitches)}"
        )

    pitch_span = max(pitches) - min(pitches)
    if pitch_span < 5:
        raise MelodyValidationError(
            f"track 0 pitch span must be at least 5 semitones; got {pitch_span}"
        )

    intervals = [b - a for a, b in zip(pitches, pitches[1:])]
    moving_intervals = [abs(i) for i in intervals if i != 0]
    if len(moving_intervals) < 3:
        raise MelodyValidationError("track 0 needs clearer melodic motion")

    if max(moving_intervals) > 12:
        raise MelodyValidationError("track 0 has a leap larger than one octave")

    if sum(1 for n in score.notes if n.track in (2, 3)) > len(beacon) + 2:
        raise MelodyValidationError(
            "static/relay notes are crowding the beacon melody; reduce tracks 2 and 3"
        )

