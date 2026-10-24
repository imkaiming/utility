from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from engine import Waveform


SAMPLE_RATE = 48000
CHANNELS = 1
SUBTYPE = "PCM_24"
QUANTIZATION_STEP = 2.0 ** -23


def export_wav(waveform: Waveform, path: Path) -> dict:
    samples = waveform.samples
    if waveform.sample_rate != SAMPLE_RATE:
        raise ValueError("Expected generated audio at 48000 Hz; no resampling is allowed")
    if not isinstance(samples, np.ndarray) or samples.ndim != 1 or samples.size == 0:
        raise ValueError("Expected a nonempty mono waveform array")
    if samples.dtype.kind != "f" or not np.isfinite(samples).all():
        raise ValueError("Waveform must contain finite floating-point samples")
    if samples.min() < -1 or samples.max() >= 1:
        raise ValueError("Waveform exceeds PCM range; refusing clipping or normalization")

    # Exclusive creation preserves existing files. No input audio file or codec is involved.
    with path.open("xb") as output:
        sf.write(output, samples, SAMPLE_RATE, format="WAV", subtype=SUBTYPE)
    info = sf.info(path)
    if (info.format, info.subtype, info.samplerate, info.channels, info.frames) != (
        "WAV", SUBTYPE, SAMPLE_RATE, CHANNELS, samples.size,
    ):
        raise RuntimeError("Exported WAV failed format verification")
    decoded, rate = sf.read(path, dtype="float64")
    if rate != SAMPLE_RATE or decoded.shape != samples.shape or not np.all(
        np.abs(decoded - samples) <= QUANTIZATION_STEP
    ):
        raise RuntimeError("Exported samples differ beyond 24-bit quantization tolerance")
    return {
        "format": info.format, "subtype": info.subtype,
        "sample_rate": info.samplerate, "channels": info.channels,
        "frames": info.frames, "duration_seconds": info.frames / SAMPLE_RATE,
        "peak": float(np.abs(samples).max()),
        "waveform_sha256": hashlib.sha256(samples.tobytes(order="C")).hexdigest(),
        "waveform_dtype": str(samples.dtype),
        "wav_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
