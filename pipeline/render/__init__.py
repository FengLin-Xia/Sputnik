"""
Render layer: minimal score.json → cold broadcast WAV (v0.1).

Not a general music engine — Sputnik-specific timbres and fixed beat grid.
"""

from pipeline.render.exporter import export_wav_mono, render_file_to_wav, render_score_to_wav
from pipeline.render.schema import Note, Score, load_score, validate_score
from pipeline.render.synth import DEFAULT_SAMPLE_RATE, render_score

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
