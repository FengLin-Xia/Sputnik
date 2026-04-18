"""Light broadcast delay, hiss, simple tone shaping — not a full mix bus."""

from __future__ import annotations

import numpy as np


def apply_light_delay(
    audio: np.ndarray,
    sample_rate: int,
    delay_s: float = 0.078,
    wet: float = 0.11,
) -> np.ndarray:
    """Single short echo for distance / transmitter slapback (not room reverb)."""
    x = np.asarray(audio, dtype=np.float64)
    d = max(1, int(delay_s * sample_rate))
    n = x.shape[0]
    if n == 0:
        return audio.astype(np.float32)
    delayed = np.zeros(n, dtype=np.float64)
    if d < n:
        delayed[d:] = x[:-d]
    out = (1.0 - wet) * x + wet * delayed
    return out.astype(np.float32)


def apply_broadcast_hiss(
    audio: np.ndarray,
    sample_rate: int,
    rng: np.random.Generator,
    level: float = 0.012,
) -> np.ndarray:
    """Weak wideband hiss + high-frequency tilt (carrier / cheap receiver)."""
    x = np.asarray(audio, dtype=np.float64)
    n = x.shape[0]
    if n == 0:
        return audio.astype(np.float32)
    hiss = rng.standard_normal(n).astype(np.float64)
    # high emphasis
    if n > 1:
        hiss = np.diff(hiss, prepend=hiss[0])
        hiss *= 0.35
    hiss *= level
    return (x + hiss).astype(np.float32)


def apply_one_pole_highpass(audio: np.ndarray, sample_rate: int, hz: float = 180.0) -> np.ndarray:
    """Remove mud; keeps cold, thin broadcast balance."""
    x = np.asarray(audio, dtype=np.float64)
    if x.size < 2:
        return audio.astype(np.float32)
    dt = 1.0 / float(sample_rate)
    rc = 1.0 / (2.0 * np.pi * hz)
    alpha = rc / (rc + dt)
    y = np.zeros_like(x)
    y[0] = x[0]
    for i in range(1, x.shape[0]):
        y[i] = alpha * (y[i - 1] + x[i] - x[i - 1])
    return y.astype(np.float32)


def master_soft_limit(audio: np.ndarray, drive: float = 0.96) -> np.ndarray:
    """Gentle tanh limiting before int16 export."""
    x = np.asarray(audio, dtype=np.float64) * drive
    return np.tanh(x).astype(np.float32)


def process_broadcast_chain(
    audio: np.ndarray,
    sample_rate: int,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Delay -> hiss -> highpass -> limiter."""
    if rng is None:
        rng = np.random.default_rng(42)
    x = apply_light_delay(audio, sample_rate)
    x = apply_broadcast_hiss(x, sample_rate, rng)
    x = apply_one_pole_highpass(x, sample_rate, hz=160.0)
    x = master_soft_limit(x, drive=0.94)
    return x
