"""Speech-aware acoustic features for the local voice module."""
from pathlib import Path
import json

import librosa
import numpy as np
import onnxruntime as ort
import parselmouth
import pyloudnorm as pyln
from scipy import ndimage, signal

ROOT = Path(__file__).resolve().parents[1]
RATE = 24000
BANDS = [(100, 250), (250, 500), (500, 1000), (1000, 2000),
         (2000, 4000), (4000, 8000), (8000, 11000)]


def load(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    x, sr = librosa.load(path, sr=RATE, mono=True)
    return x.astype(np.float64)


def speech_regions(x, sr=RATE):
    """Silero ONNX, 32 ms frames. Bridge <=160 ms gaps; report >=128 ms pauses."""
    y = librosa.resample(x.astype(np.float32), orig_sr=sr, target_sr=16000)
    options = ort.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    model = ort.InferenceSession(str(ROOT / "media/voice-analysis/silero_vad.onnx"),
                                 sess_options=options, providers=["CPUExecutionProvider"])
    state = np.zeros((2, 1, 128), dtype=np.float32)
    context = np.zeros((1, 64), dtype=np.float32)
    probabilities = []
    for i in range(0, len(y), 512):
        chunk = np.pad(y[i:i + 512], (0, max(0, 512 - len(y[i:i + 512]))))[None, :]
        inputs = np.concatenate([context, chunk], axis=1)
        probability, state = model.run(None, {"input": inputs, "state": state, "sr": np.array(16000, dtype=np.int64)})
        probabilities.append(float(probability.item()))
        context = inputs[:, -64:]
    mask = np.array(probabilities) > 0.5
    # Close short holes without shifting utterance starts/ends.
    spans = runs(mask)
    for a, b, active in spans:
        if not active and a > 0 and b < len(mask) and b - a <= 5:
            mask[a:b] = True
    regions = [(a * .032, min(b * .032, len(x) / sr)) for a, b, active in runs(mask)
               if active and b - a >= 3]
    return regions, probabilities


def runs(mask):
    edges = np.r_[0, np.flatnonzero(np.diff(mask.astype(int))) + 1, len(mask)]
    return [(int(a), int(b), bool(mask[a])) for a, b in zip(edges[:-1], edges[1:]) if b > a]


def quantile(x, q, default=0.0):
    return float(np.percentile(x, q)) if len(x) else default


def analyze(x, sr=RATE, regions=None):
    if regions is None:
        regions, _ = speech_regions(x, sr)
    duration = len(x) / sr
    # Full-recording autocorrelation pitch; identical settings for every candidate.
    sound = parselmouth.Sound(x, sampling_frequency=sr)
    pitch = sound.to_pitch_ac(time_step=.01, pitch_floor=60, pitch_ceiling=300,
                              voicing_threshold=.6, silence_threshold=.05)
    f0 = pitch.selected_array["frequency"]
    confidence = pitch.selected_array["strength"]
    pitch_time = pitch.xs()
    voice_mask = np.zeros(len(f0), dtype=bool)
    for a, b in regions:
        voice_mask |= (pitch_time >= a) & (pitch_time < b)
    valid = (f0 > 0) & (confidence >= .6) & voice_mask
    hz = f0[valid]
    semitones = 12 * np.log2(hz / 100)
    pair = valid[:-1] & valid[1:]
    # Differences reflect micro-prosody and phonetic content; diagnostic, not exact-match target.
    f0_safe = np.where(f0 > 0, f0, 100)
    steps = np.abs(np.diff(12 * np.log2(f0_safe / 100)))[pair]
    harmonicity = sound.to_harmonicity_ac(time_step=.01, minimum_pitch=60,
                                         silence_threshold=.1, periods_per_window=4.5)
    hnr = harmonicity.values.ravel()
    htimes = harmonicity.xs()
    hmask = np.zeros(len(hnr), dtype=bool)
    for a, b in regions:
        hmask |= (htimes >= a) & (htimes < b)
    hnr = hnr[hmask & (hnr > -50) & np.isfinite(hnr)]
    _, times, z = signal.stft(x, fs=sr, nperseg=1024, noverlap=768, boundary="zeros")
    power = np.abs(z) ** 2
    frequency = np.fft.rfftfreq(1024, 1 / sr)
    active = np.zeros(len(times), dtype=bool)
    for a, b in regions:
        active |= (times >= a) & (times < b)
    active &= power.sum(axis=0) > max(float(power.sum(axis=0).max()) * .002, 1e-12)
    p = power[:, active]
    if p.shape[1] < 5 or len(hz) < 5:
        raise ValueError("Insufficient detected speech for reliable measurement")
    bands = np.array([p[(frequency >= a) & (frequency < b)].sum() for a, b in BANDS])
    band_db = 10 * np.log10(np.maximum(bands, 1e-20) / bands.sum())
    centroid = (p * frequency[:, None]).sum(axis=0) / np.maximum(p.sum(axis=0), 1e-20)
    cumulative = np.cumsum(p, axis=0)
    rolloff = frequency[np.argmax(cumulative >= cumulative[-1] * .85, axis=0)]
    high = p[(frequency >= 4000) & (frequency <= 10000)].sum(axis=0)
    low = p[(frequency >= 100) & (frequency < 4000)].sum(axis=0)
    ratios = 10 * np.log10(np.maximum(high, 1e-20) / np.maximum(low, 1e-20))
    # Spectral flatness is a noise-like texture proxy, including unvoiced consonants.
    flat_band = p[(frequency >= 1000) & (frequency < 8000)]
    flatness = np.exp(np.mean(np.log(flat_band + 1e-20), axis=0)) / np.mean(flat_band + 1e-20, axis=0)
    rms = np.sqrt(np.mean(x ** 2))
    frame_rms = np.sqrt(np.maximum(power.sum(axis=0), 1e-20))
    level = 20 * np.log10(frame_rms[active] + 1e-20)
    envelope = ndimage.gaussian_filter1d(frame_rms, 2)
    mf, mp = signal.welch(envelope, fs=sr / 256, nperseg=min(len(envelope), 512))
    modulation = (mf >= .5) & (mf <= 8)
    mod_peak = float(mf[modulation][np.argmax(mp[modulation])])
    gaps = [regions[i + 1][0] - regions[i][1] for i in range(len(regions) - 1)]
    gaps = np.array([g for g in gaps if g >= .128])
    speech_seconds = sum(b - a for a, b in regions)
    within = max(regions[-1][1] - regions[0][0], .01)
    result = {
        "duration_seconds": duration,
        "pitch_median_hz": quantile(hz, 50), "pitch_p10_hz": quantile(hz, 10), "pitch_p90_hz": quantile(hz, 90),
        "pitch_p25_hz": quantile(hz, 25), "pitch_p75_hz": quantile(hz, 75),
        "pitch_iqr_semitones": quantile(semitones, 75) - quantile(semitones, 25),
        "pitch_range80_semitones": quantile(semitones, 90) - quantile(semitones, 10),
        "pitch_step_p50_semitones": quantile(steps, 50), "pitch_step_p90_semitones": quantile(steps, 90),
        "hnr_median_db": quantile(hnr, 50), "hnr_iqr_db": quantile(hnr, 75) - quantile(hnr, 25),
        "centroid_median_hz": quantile(centroid, 50), "rolloff85_median_hz": quantile(rolloff, 50),
        "sibilance_p90_db": quantile(ratios, 90), "sibilance_p50_db": quantile(ratios, 50),
        "flatness_median": quantile(flatness, 50),
        "integrated_lufs": float(pyln.Meter(sr).integrated_loudness(x)),
        "rms_dbfs": float(20 * np.log10(max(rms, 1e-12))),
        "sample_peak_dbfs": float(20 * np.log10(max(np.max(np.abs(x)), 1e-12))),
        "crest_db": float(20 * np.log10(max(np.max(np.abs(x)), 1e-12) / max(rms, 1e-12))),
        "active_level_range80_db": quantile(level, 90) - quantile(level, 10),
        "active_level_iqr_db": quantile(level, 75) - quantile(level, 25),
        "pause_fraction_internal": max(0., 1 - speech_seconds / within),
        "pause_median_seconds": quantile(gaps, 50), "pause_p90_seconds": quantile(gaps, 90),
        "pauses_per_minute": len(gaps) / within * 60,
        "speech_run_median_seconds": quantile([b - a for a, b in regions], 50),
        "envelope_modulation_peak_hz": mod_peak,
    }
    result.update({f"band_{a}_{b}_db": float(db) for (a, b), db in zip(BANDS, band_db)})
    return result, {"regions": regions, "pitch_time": pitch_time, "pitch_hz": f0,
                    "pitch_valid": valid, "band_db": band_db, "frame_times": times, "frame_rms": frame_rms,
                    "active_frames": active}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for path in args.files:
        result, detail = analyze(load(path))
        results.append({"file": str(path), "metrics": result, "speech_regions": detail["regions"]})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
