"""Write mono PCM WAV (16-bit)."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from pipeline.render.effects import process_broadcast_chain
from pipeline.render.schema import Score, load_score
from pipeline.render.synth import DEFAULT_SAMPLE_RATE, render_score


def export_wav_mono(
    audio: np.ndarray,
    path: str | Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> None:
    """Float32 mono [-1,1] -> 16-bit WAV."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    x = np.asarray(audio, dtype=np.float64)
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767.0).astype(np.int16)
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def render_score_to_wav(
    score: Score,
    out_path: str | Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int | None = 42,
) -> None:
    dry = render_score(score, sample_rate=sample_rate, seed=seed)
    rng = np.random.default_rng(seed)
    wet = process_broadcast_chain(dry, sample_rate, rng=rng)
    export_wav_mono(wet, out_path, sample_rate=sample_rate)


def render_file_to_wav(
    score_path: str | Path,
    out_path: str | Path,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int | None = 42,
) -> None:
    score = load_score(score_path)
    render_score_to_wav(score, out_path, sample_rate=sample_rate, seed=seed)
