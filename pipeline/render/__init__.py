"""
Render layer: minimal score.json → cold broadcast WAV (v0.1).

Heavy modules (numpy/synth) load lazily so composition can import schema only.
"""

from __future__ import annotations

from pipeline.render.schema import Note, Score, load_score, validate_score

__all__ = [
    "DEFAULT_SAMPLE_RATE",
    "Note",
    "Score",
    "export_wav_mono",
    "load_score",
    "render_file_to_wav",
    "render_score",
    "render_score_to_wav",
    "validate_score",
]


def __getattr__(name: str):
    if name == "export_wav_mono":
        from pipeline.render.exporter import export_wav_mono

        return export_wav_mono
    if name == "render_file_to_wav":
        from pipeline.render.exporter import render_file_to_wav

        return render_file_to_wav
    if name == "render_score_to_wav":
        from pipeline.render.exporter import render_score_to_wav

        return render_score_to_wav
    if name == "render_score":
        from pipeline.render.synth import render_score

        return render_score
    if name == "DEFAULT_SAMPLE_RATE":
        from pipeline.render.synth import DEFAULT_SAMPLE_RATE

        return DEFAULT_SAMPLE_RATE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
