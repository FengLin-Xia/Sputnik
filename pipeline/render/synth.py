"""Note grid -> waveforms, multi-track mix. Render v0.1 cold broadcast timbres."""

from __future__ import annotations

import numpy as np

from pipeline.render.schema import Note, Score

DEFAULT_SAMPLE_RATE = 44100


def midi_to_hz(p: float) -> float:
    return 440.0 * (2.0 ** ((float(p) - 69.0) / 12.0))


def _triangle(phase: np.ndarray) -> np.ndarray:
    """phase in [0,1) per period."""
    return 2.0 * np.abs(2.0 * (phase - np.floor(phase + 0.5))) - 1.0


def _adsr_linear(n_samples: int, sr: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    """Piecewise-linear ADSR envelope, length n_samples."""
    env = np.zeros(max(0, n_samples), dtype=np.float64)
    if n_samples <= 0:
        return env
    pos = 0
    a_n = min(int(a * sr), n_samples - pos)
    if a_n > 0:
        env[pos : pos + a_n] = np.linspace(0.0, 1.0, a_n, endpoint=False)
        pos += a_n
    d_n = min(int(d * sr), n_samples - pos)
    if d_n > 0:
        env[pos : pos + d_n] = np.linspace(1.0, s, d_n, endpoint=False)
        pos += d_n
    r_start = n_samples - int(r * sr)
    r_start = max(pos, min(r_start, n_samples))
    if r_start > pos:
        env[pos:r_start] = s
    r_n = n_samples - r_start
    if r_n > 0:
        start_level = float(env[r_start - 1]) if r_start > 0 else s
        env[r_start:] = np.linspace(start_level, 0.0, r_n, endpoint=True)
    return np.clip(env, 0.0, 1.0)


def _render_note_beacon(
    n: Note, n_samples: int, sr: int, _t0: int, rng: np.random.Generator
) -> np.ndarray:
    """Track 0: thin triangle lead, slight pitch drift."""
    hz = midi_to_hz(n.p)
    t = np.arange(n_samples, dtype=np.float64) / sr
    drift = 1.0 + 0.003 * np.sin(2.0 * np.pi * 0.37 * t)
    phase = (t * hz * drift) % 1.0
    osc = _triangle(phase)
    a, d, s, r = 0.004, 0.06, 0.55, 0.12
    env = _adsr_linear(n_samples, sr, a, d, s, r)
    gain = 0.22 * float(n.v)
    return (osc * env * gain).astype(np.float64)


def _render_note_drone(
    n: Note, n_samples: int, sr: int, _t0: int, _rng: np.random.Generator
) -> np.ndarray:
    """Track 1: low sine + tiny upper partial, long envelope."""
    hz = midi_to_hz(n.p)
    t = np.arange(n_samples, dtype=np.float64) / sr
    fundamental = np.sin(2.0 * np.pi * hz * t)
    partial = 0.08 * np.sin(2.0 * np.pi * hz * 2.003 * t)
    osc = fundamental + partial
    a, d, s, r = 0.08, 0.12, 0.82, 0.45
    env = _adsr_linear(n_samples, sr, a, d, s, r)
    gain = 0.14 * float(n.v)
    return (osc * env * gain).astype(np.float64)


def _render_note_static(
    n: Note, n_samples: int, sr: int, _t0: int, rng: np.random.Generator
) -> np.ndarray:
    """Track 2: short band-limited noise bursts + occasional click."""
    noise = rng.standard_normal(n_samples).astype(np.float64)
    # crude high emphasis (ghost hiss)
    if n_samples > 2:
        emphasized = np.diff(noise, prepend=noise[0])
        emphasized = emphasized * 0.5 + noise * 0.5
    else:
        emphasized = noise
    a, d, s, r = 0.001, 0.04, 0.15, 0.09
    env = _adsr_linear(n_samples, sr, a, d, s, r)
    gain = 0.09 * float(n.v)
    burst = emphasized * env * gain
    # sparse micro-clicks at note on
    if n_samples > 0:
        click = np.zeros(n_samples, dtype=np.float64)
        c = min(64, n_samples)
        click[:c] = rng.standard_normal(c) * np.linspace(0.25, 0.0, c, endpoint=False)
        burst = burst + click * 0.06 * float(n.v)
    return burst


def _render_note_relay(
    n: Note, n_samples: int, sr: int, _t0: int, _rng: np.random.Generator
) -> np.ndarray:
    """Track 3: short FM / glass ping — distant telemetry, not competing with lead."""
    hz = midi_to_hz(n.p)
    t = np.arange(n_samples, dtype=np.float64) / sr
    mod_hz = max(2.0, hz * 0.22)
    # mild FM for metallic cold ping; index kept low so it stays thin
    mod_idx = 0.55 + 0.15 * np.sin(2.0 * np.pi * 0.31 * t)
    phase = 2.0 * np.pi * hz * t + mod_idx * np.sin(2.0 * np.pi * mod_hz * t)
    osc = np.sin(phase)
    a, d, s, r = 0.002, 0.14, 0.22, 0.28
    env = _adsr_linear(n_samples, sr, a, d, s, r)
    gain = 0.11 * float(n.v)
    return (osc * env * gain).astype(np.float64)


_RENDERERS = {
    0: _render_note_beacon,
    1: _render_note_drone,
    2: _render_note_static,
    3: _render_note_relay,
}


def render_score(
    score: Score,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    seed: int | None = 42,
) -> np.ndarray:
    """
    Render full score to mono float32 array in [-1, 1] (may clip slightly before master FX).
    """
    beats_total = score.total_beats
    seconds = beats_total * 60.0 / float(score.bpm)
    total_samples = int(np.ceil(seconds * sample_rate))
    rng = np.random.default_rng(seed)
    mix = np.zeros(total_samples, dtype=np.float64)
    spb = sample_rate * 60.0 / float(score.bpm)  # samples per beat

    for n in score.notes:
        t0 = int(round(n.t * spb))
        n_len = int(round(n.d * spb))
        if n_len <= 0 or t0 >= total_samples:
            continue
        n_len = min(n_len, total_samples - t0)
        renderer = _RENDERERS.get(n.track, _render_note_beacon)
        segment = renderer(n, n_len, sample_rate, t0, rng)
        if segment.shape[0] != n_len:
            segment = segment[:n_len]
        mix[t0 : t0 + n_len] += segment

    peak = np.max(np.abs(mix)) if mix.size else 0.0
    if peak > 1e-12:
        mix = mix / peak * 0.92
    return mix.astype(np.float32)


