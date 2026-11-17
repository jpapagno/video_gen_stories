"""CPU-only, constrained prosody and mix matching with explicit acoustic scorecard."""
import argparse
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import parselmouth
import pyloudnorm as pyln
import soundfile as sf
from parselmouth.praat import call
from scipy import ndimage, signal

from .features import ROOT, RATE, BANDS, analyze, load


def save(path, x):
    if not np.isfinite(x).all() or not len(x):
        raise ValueError("Invalid audio")
    if np.max(np.abs(x)) >= .99:
        raise ValueError("Peak exceeds output ceiling")
    sf.write(path, x, RATE, subtype="PCM_24")


def pitch_match(x, reference, source, strength, micro_gain=0.):
    sound = parselmouth.Sound(x, sampling_frequency=RATE)
    manipulation = call(sound, "To Manipulation", .01, 60, 300)
    tier = call(manipulation, "Extract pitch tier")
    new_tier = call("Create PitchTier", "matched", sound.xmin, sound.xmax)
    keys = ["pitch_p10_hz", "pitch_p25_hz", "pitch_median_hz", "pitch_p75_hz", "pitch_p90_hz"]
    src = np.log([source[k] for k in keys])
    dst = np.log([reference[k] for k in keys])
    n = int(call(tier, "Get number of points"))
    tier_values = np.array([call(tier, "Get value at index", i) for i in range(1, n + 1)])
    micro = np.log(tier_values) - ndimage.gaussian_filter1d(np.log(tier_values), 5)
    for i in range(1, n + 1):
        t = call(tier, "Get time from index", i)
        hz = call(tier, "Get value at index", i)
        log_hz = np.log(hz)
        # Quantile map inside measured range; gentle extrapolation retains variation.
        mapped = np.interp(log_hz, src, dst)
        if log_hz < src[0]:
            mapped += .7 * (log_hz - src[0])
        if log_hz > src[-1]:
            mapped += .7 * (log_hz - src[-1])
        value = np.exp((1 - strength) * log_hz + strength * mapped + micro_gain * micro[i - 1])
        call(new_tier, "Add point", t, float(np.clip(value, 65, 220)))
    call([new_tier, manipulation], "Replace pitch tier")
    return call(manipulation, "Get resynthesis (overlap-add)").values[0].copy()


def pace_match(x, ref_details, source_details, target_duration, folder, strength):
    regions = source_details["regions"]
    ref_regions = ref_details["regions"]
    gaps = np.array([regions[i + 1][0] - regions[i][1] for i in range(len(regions) - 1)])
    ref_gaps = np.array([ref_regions[i + 1][0] - ref_regions[i][1] for i in range(len(ref_regions) - 1)])
    if not len(gaps) or not len(ref_gaps):
        return x, {}
    ref_inside = ref_regions[-1][1] - ref_regions[0][0]
    pause_fraction = ref_gaps.sum() / ref_inside
    desired_count = int(np.clip(round(len(ref_gaps) / ref_inside * target_duration), 1, len(gaps)))
    ranked = np.argsort(gaps)
    proposed = np.full(len(gaps), .12)
    selected = ranked[-desired_count:]
    quantiles = np.quantile(ref_gaps, (np.arange(desired_count) + .5) / desired_count)
    proposed[selected] = quantiles
    # Maintain matched global WPM while moving duration from pauses into speech.
    budget = pause_fraction * target_duration
    for _ in range(3):
        proposed *= budget / proposed.sum()
        proposed = np.maximum(proposed, .12)
    desired = (1 - strength) * gaps + strength * proposed
    speech_and_edges = len(x) / RATE - gaps.sum()
    rate = speech_and_edges / max(target_duration - desired.sum(), .1)
    rate = float(np.clip(rate, .75, 1.1))
    sf.write(folder / "pace-input.wav", x, RATE, subtype="FLOAT")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", str(folder / "pace-input.wav"),
                    "-af", f"atempo={rate:.8f}", "-c:a", "pcm_f32le", str(folder / "pace-stretched.wav")], check=True)
    stretched, _ = sf.read(folder / "pace-stretched.wav")
    pieces, cursor = [], 0
    edits = []
    for i, new_gap in enumerate(desired):
        a = int(regions[i][1] / rate * RATE)
        b = int(regions[i + 1][0] / rate * RATE)
        a, b = min(a, len(stretched)), min(b, len(stretched))
        pieces.append(stretched[cursor:a])
        old = stretched[a:b]
        count = max(1, round(new_gap * RATE))
        if count < len(old):
            edge = min(round(.06 * RATE), count // 2, len(old) // 2)
            middle = count - 2 * edge
            # Preserve phonetic edges. Only shorten the central detected gap.
            if middle:
                center = old[len(old) // 2 - middle // 2:len(old) // 2 - middle // 2 + middle]
                new = np.r_[old[:edge], center, old[-edge:]]
            else:
                new = np.r_[old[:edge], old[-edge:]]
            # Crossfade tiny discontinuities at splice points.
            for seam in (edge, edge + middle):
                radius = min(48, seam, len(new) - seam - 1)
                if radius > 0:
                    new[seam - radius:seam + radius] = np.linspace(new[seam - radius], new[seam + radius], 2 * radius)
        else:
            middle = len(old) // 2
            new = np.r_[old[:middle], np.zeros(count - len(old)), old[middle:]]
        pieces.append(new)
        cursor = b
        edits.append({"old_gap_seconds": float(gaps[i]), "new_gap_seconds": len(new) / RATE})
    pieces.append(stretched[cursor:])
    return np.concatenate(pieces), {"speech_tempo": rate, "pause_edits": edits}


def spectral_match(x, reference, current, strength, accumulated, precise=False):
    keys = [f"band_{a}_{b}_db" for a, b in BANDS]
    error = np.array([reference[k] - current[k] for k in keys])
    gains = (error if precise else ndimage.gaussian_filter1d(error, .65)) * strength
    gains -= np.mean(gains)
    new_total = np.clip(accumulated + gains, -6 if precise else -5, 6 if precise else 5)
    gains = new_total - accumulated
    centers = np.array([np.sqrt(a * b) for a, b in BANDS])
    freq, _, z = signal.stft(x, fs=RATE, nperseg=2048, noverlap=1536, boundary="zeros")
    if precise:
        curve = np.zeros(len(freq))
        for (a, b), db in zip(BANDS, gains):
            curve[(freq >= a) & (freq < b)] = db
        curve[freq < BANDS[0][0]] = gains[0]
        curve[freq >= BANDS[-1][1]] = gains[-1]
        curve = ndimage.gaussian_filter1d(curve, 3)
    else:
        curve = np.interp(np.log(np.maximum(freq, 30)), np.log(centers), gains)
    z *= 10 ** (curve[:, None] / 20)
    _, audio = signal.istft(z, fs=RATE, nperseg=2048, noverlap=1536, boundary=True)
    return audio[:len(x)], new_total


def dynamics_match(x, reference, current, detail, strength):
    rms = detail["frame_rms"]
    active = detail["active_frames"]
    db = 20 * np.log10(rms + 1e-12)
    ratio = np.clip(reference["active_level_iqr_db"] / max(current["active_level_iqr_db"], .1), .8, 1.2)
    gain_db = np.clip((ratio - 1) * (db - np.median(db[active])) * strength, -2, 2)
    gain_db = ndimage.gaussian_filter1d(gain_db, 8)
    times = np.arange(len(x)) / RATE
    gain = np.interp(times, detail["frame_times"], gain_db)
    x = x * 10 ** (gain / 20)
    # Smooth, bounded peak reduction. Preserve quiet samples and avoid hard clipping.
    target_crest = (1 - strength) * current["crest_db"] + strength * reference["crest_db"]
    def limit(threshold):
        return x / (1 + (np.abs(x) / threshold) ** 8) ** (1 / 8)
    left, right = max(np.sqrt(np.mean(x ** 2)) * .8, .001), max(np.max(np.abs(x)) * 8, .01)
    for _ in range(25):
        mid = (left + right) / 2
        y = limit(mid)
        crest = 20 * np.log10(np.max(np.abs(y)) / np.sqrt(np.mean(y ** 2)))
        if crest > target_crest:
            right = mid
        else:
            left = mid
    return limit((left + right) / 2)


def level_match(x, target_lufs):
    measured = pyln.Meter(RATE).integrated_loudness(x)
    return x * 10 ** ((target_lufs - measured) / 20)


def deess(x, target, current):
    """Compress the distribution of high/low-band ratios, rather than dull all consonants."""
    frequency, _, z = signal.stft(x, fs=RATE, nperseg=1024, noverlap=768, boundary="zeros")
    p = np.abs(z) ** 2
    hi = p[(frequency >= 4000) & (frequency <= 10000)].sum(axis=0)
    lo = p[(frequency >= 100) & (frequency < 4000)].sum(axis=0)
    ratio = 10 * np.log10((hi + 1e-20) / (lo + 1e-20))
    source_span = max(current["sibilance_p90_db"] - current["sibilance_p50_db"], 1)
    target_span = max(target["sibilance_p90_db"] - target["sibilance_p50_db"], 1)
    desired = target["sibilance_p50_db"] + (ratio - current["sibilance_p50_db"]) * target_span / source_span
    gains = ndimage.gaussian_filter1d(np.clip(desired - ratio, -5, 4), 1.5)
    blend = np.clip((frequency - 3000) / 2000, 0, 1)
    z *= 10 ** (blend[:, None] * gains[None, :] / 20)
    _, out = signal.istft(z, fs=RATE, nperseg=1024, noverlap=768, boundary=True)
    return out[:len(x)]


def level_shape(x, target_detail, detail):
    """Map active envelope quantiles with a bounded, smoothly varying gain."""
    db = 20 * np.log10(detail["frame_rms"] + 1e-12)
    ref_db = 20 * np.log10(target_detail["frame_rms"] + 1e-12)
    q = [10, 25, 50, 75, 90]
    source_q = np.percentile(db[detail["active_frames"]], q)
    target_q = np.percentile(ref_db[target_detail["active_frames"]], q)
    target_q += source_q[2] - target_q[2]
    mapped = np.interp(db, source_q, target_q)
    gains = np.clip(mapped - db, -2, 2)
    gains = ndimage.gaussian_filter1d(gains, 3)
    samples_gain = np.interp(np.arange(len(x)) / RATE, detail["frame_times"], gains)
    return x * 10 ** (samples_gain / 20)


def air_layer(x, detail, amount):
    """Low-level synthetic aspiration proxy, gated to detected voiced speech."""
    rng = np.random.default_rng(20261115)
    noise = rng.standard_normal(len(x))
    noise = signal.sosfilt(signal.butter(3, [200, 6500], fs=RATE, btype="bandpass", output="sos"), noise)
    gate = np.interp(np.arange(len(x)) / RATE, detail["pitch_time"], detail["pitch_valid"].astype(float))
    gate = ndimage.gaussian_filter1d(gate, RATE * .02)
    envelope = np.interp(np.arange(len(x)) / RATE, detail["frame_times"], detail["frame_rms"])
    noise *= gate * envelope
    noise *= np.sqrt(np.mean(x ** 2)) / max(np.sqrt(np.mean(noise ** 2)), 1e-12)
    return x + amount * noise


def uncertainty(reference, details):
    segments = []
    for i in range(3):
        a = i * 20
        regions = [(max(0, start - a), min(20, end - a)) for start, end in details["regions"]
                   if end > a and start < a + 20]
        value, _ = analyze(reference[a * RATE:(a + 20) * RATE], regions=regions)
        segments.append(value)
    return {key: {"min": min(s[key] for s in segments), "max": max(s[key] for s in segments)}
            for key in segments[0]}, segments


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=Path("media/sleep-reference.wav"))
    parser.add_argument("--source", type=Path, default=Path("outputs/sleep-story/qwen/reference-iterations/v2-low-rounded-tuned.wav"))
    parser.add_argument("--out", type=Path, default=Path("outputs/sleep-story/qwen/metric-match"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    reference, source = load(args.reference), load(args.source)
    target, ref_detail = analyze(reference)
    before, source_detail = analyze(source)
    intervals, segments = uncertainty(reference, ref_detail)
    candidates = []
    for name, strength in [("v4-gentle-match", .55), ("v5-full-match", 1.0)]:
        print(f"Refining {name}: pitch contour and speech/pause timing", flush=True)
        x = pitch_match(source, target, before, strength)
        after_pitch, pitch_details = analyze(x)
        # A second small quantile correction handles estimator/resynthesis differences.
        if strength == 1:
            x = pitch_match(x, target, after_pitch, .6)
            after_pitch, pitch_details = analyze(x)
        x, pace = pace_match(x, ref_detail, pitch_details, len(source) / RATE, args.out, strength)
        accumulated = np.zeros(len(BANDS))
        history = []
        for iteration in range(4):
            current, detail = analyze(x)
            history.append(current)
            x, accumulated = spectral_match(x, target, current, strength * .75, accumulated)
            if iteration == 0:
                x = dynamics_match(x, target, current, detail, strength)
            x = level_match(x, target["integrated_lufs"])
        final, detail = analyze(x)
        path = args.out / f"{name}.wav"
        save(path, x)
        candidates.append({"name": name, "file": str(path), "strength": strength,
                           "metrics": final, "processing": {"eq_band_gain_db": accumulated.tolist(), **pace},
                           "history": history, "speech_regions": detail["regions"]})
        print(f"Saved {path}", flush=True)
    report = {"reference": str(args.reference), "source": str(args.source),
              "reference_metrics": target, "reference_20s_ranges": intervals,
              "reference_20s_segments": segments, "before_metrics": before,
              "candidates": candidates,
              "limitations": ["Reference contains background audio; HNR/flatness include mix effects.",
                              "Different words change formants, sibilance, phonetic timing and spectral balance.",
                              "No speaker identity or accent matching score is inferred from these statistics.",
                              "HNR and flatness are diagnostics, not forcibly matched by adding background hiss.",
                              "Pause edits preserve 60 ms phonetic edges; listen for artifacts before production."]}
    (args.out / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Full comparison saved.")
