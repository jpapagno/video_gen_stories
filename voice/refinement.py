"""Second pass: retain micro-prosody, dynamic de-essing, band matching and restrained air."""
import json
from pathlib import Path

import numpy as np

from .features import ROOT, BANDS, RATE, analyze, load
from .processing import (air_layer, deess, dynamics_match, level_match, level_shape,
                               pace_match, pitch_match, save, spectral_match)

OUT = ROOT / "outputs/sleep-story/qwen/metric-match"


def score(metrics, target, uncertainty):
    # Correlated feature groups are normalized separately; this is NOT a similarity percentage.
    groups = [(["pitch_median_hz", "pitch_p10_hz", "pitch_p90_hz"], 4.),
              (["pitch_iqr_semitones", "pitch_range80_semitones"], .7),
              (["pitch_step_p50_semitones", "pitch_step_p90_semitones"], .1),
              ([f"band_{a}_{b}_db" for a, b in BANDS], 2.),
              (["sibilance_p50_db", "sibilance_p90_db"], 3.),
              (["crest_db", "active_level_iqr_db", "active_level_range80_db"], 2.),
              (["pause_fraction_internal"], .04),
              (["pause_median_seconds", "pause_p90_seconds"], .2),
              (["hnr_median_db"], 4.)]
    errors = []
    for keys, floor in groups:
        errors.append(np.mean([abs(metrics[k] - target[k]) /
                              max(floor, (uncertainty[k]["max"] - uncertainty[k]["min"]) / 2)
                              for k in keys]))
    return float(np.mean(errors))


if __name__ == "__main__":
    report = json.loads((OUT / "comparison.json").read_text())
    source = load(report["source"])
    reference = load(report["reference"])
    target, ref_detail = analyze(reference)
    before, source_detail = analyze(source)
    extra = []
    for name, micro in [("v6-balanced-match", .65), ("v7-textured-match", 1.2)]:
        print(f"Refining {name}", flush=True)
        x = pitch_match(source, target, before, 1., micro_gain=micro)
        pitch_metrics, pitch_detail = analyze(x)
        # Gently center pitch without repeatedly flattening the restored micro-contour.
        ratio = target["pitch_median_hz"] / pitch_metrics["pitch_median_hz"]
        if abs(np.log2(ratio)) > .015:
            # Uniform pitch correction leaves the relative fine movement intact.
            adjusted_target = dict(pitch_metrics)
            for key in ["pitch_p10_hz", "pitch_p25_hz", "pitch_median_hz", "pitch_p75_hz", "pitch_p90_hz"]:
                adjusted_target[key] *= ratio
            x = pitch_match(x, adjusted_target, pitch_metrics, 1.)
            pitch_metrics, pitch_detail = analyze(x)
        x, pace = pace_match(x, ref_detail, pitch_detail, len(source) / RATE, OUT, 1.)
        # Test a small bounded aspiration layer, not the reference's music/noise bed.
        base, detail = analyze(x)
        best_air = None
        for amount in [0., .04, .08, .12]:
            trial = air_layer(x, detail, amount) if amount else x.copy()
            measured, _ = analyze(trial, regions=detail["regions"])
            error = abs(measured["hnr_median_db"] - target["hnr_median_db"])
            if best_air is None or error < best_air[0]:
                best_air = (error, amount, trial)
        x = best_air[2]
        accumulated = np.zeros(len(BANDS))
        snapshots = []
        for iteration in range(5):
            current, detail = analyze(x)
            x = deess(x, target, current)
            current, detail = analyze(x)
            x, accumulated = spectral_match(x, target, current, .7, accumulated, precise=True)
            current, detail = analyze(x)
            x = level_shape(x, ref_detail, detail)
            if iteration in (0, 3):
                current, detail = analyze(x)
                x = dynamics_match(x, target, current, detail, 1.)
            x = level_match(x, target["integrated_lufs"])
            current, _ = analyze(x)
            snapshots.append({"score": score(current, target, report["reference_20s_ranges"]),
                              "audio": x.copy(), "metrics": current, "iteration": iteration + 1,
                              "eq_band_gain_db": accumulated.tolist()})
        best = min(snapshots, key=lambda s: s["score"])
        path = OUT / f"{name}.wav"
        save(path, best["audio"])
        extra.append({"name": name, "file": str(path), "metrics": best["metrics"],
                      "score": best["score"], "processing": {"micro_gain": micro,
                      "air_rms_fraction": best_air[1], "selected_iteration": best["iteration"],
                      "eq_band_gain_db": best["eq_band_gain_db"], **pace},
                      "iterations": [{k: v for k, v in s.items() if k != "audio"} for s in snapshots]})
        print(f"Saved {name}; objective={best['score']:.3f}", flush=True)
    report["candidates"].extend(extra)
    for candidate in report["candidates"]:
        candidate["score"] = score(candidate["metrics"], target, report["reference_20s_ranges"])
    report["baseline_score"] = score(before, target, report["reference_20s_ranges"])
    report["recommended_by_objective"] = min(report["candidates"], key=lambda c: c["score"])["name"]
    report["score_note"] = "Grouped acoustic-distance objective with reference-window variability; not an identity or perceptual similarity percentage."
    (OUT / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Recommended by objective:", report["recommended_by_objective"])
