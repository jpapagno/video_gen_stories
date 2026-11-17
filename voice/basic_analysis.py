"""Legacy basic analysis retained for comparing earlier voice auditions."""
import argparse
import json
from pathlib import Path

import librosa
import numpy as np


def measure(path):
    audio, rate = librosa.load(path, sr=16000)
    # Limit pitch analysis to 25 seconds, excluding quiet frames and low-confidence F0.
    sample = audio[:25 * rate]
    f0, voiced, probability = librosa.pyin(sample, sr=rate, fmin=55, fmax=350,
                                          frame_length=1024, hop_length=256)
    pitched = f0[voiced & (probability >= 0.5) & np.isfinite(f0)]
    spectrum = np.abs(librosa.stft(audio, n_fft=1024, hop_length=256)) ** 2
    frequency = librosa.fft_frequencies(sr=rate, n_fft=1024)
    energy = librosa.feature.rms(y=audio, frame_length=1024, hop_length=256)[0]
    active = energy > max(float(np.max(energy)) * 0.08, 0.0001)
    voice_band = spectrum[(frequency >= 100) & (frequency <= 6000), :][:, active]
    upper_band = spectrum[(frequency >= 3000) & (frequency <= 6000), :][:, active]
    metrics = {"file": str(path), "duration_seconds": len(audio) / rate,
               "pitch_median_hz": float(np.median(pitched)) if len(pitched) else None,
               "pitch_p10_hz": float(np.percentile(pitched, 10)) if len(pitched) else None,
               "pitch_p90_hz": float(np.percentile(pitched, 90)) if len(pitched) else None,
               "upper_band_energy_ratio": float(upper_band.sum() / max(voice_band.sum(), 1e-12)),
               "rms_dbfs": float(20 * np.log10(max(np.sqrt(np.mean(audio ** 2)), 1e-12))),
               "low_energy_frame_fraction": float(1 - np.mean(active)),
               "limitations": "Pitch measured from high-confidence voiced frames in first 25s. Background audio affects spectral/pause metrics. These metrics do not establish timbre, accent, or perceptual similarity."}
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = [measure(path) for path in args.files]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
