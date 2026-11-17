"""Reproduce approved V6, then remove artificial aspiration without changing its pitch/timing recipe."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from . import selected_profile
from .features import ROOT, BANDS, RATE, analyze, load
from .processing import (air_layer, deess, dynamics_match, level_match, level_shape,
                               pace_match, pitch_match, save, spectral_match)

OUT = ROOT / "outputs/sleep-story/qwen/metric-match"


def process(x, target, ref_detail, iterations):
    accumulated = np.zeros(len(BANDS))
    history = []
    for iteration in range(iterations):
        current, _ = analyze(x)
        x = deess(x, target, current)
        current, _ = analyze(x)
        x, accumulated = spectral_match(x, target, current, .7, accumulated, precise=True)
        current, detail = analyze(x)
        x = level_shape(x, ref_detail, detail)
        if iteration in (0, 3):
            current, detail = analyze(x)
            x = dynamics_match(x, target, current, detail, 1.)
        x = level_match(x, target["integrated_lufs"])
        history.append({"iteration": iteration + 1, "eq_band_gain_db": accumulated.tolist()})
    return x, history


def rebuild_v6():
    """Rebuild the selected clean audition and verify its original V6 recipe."""
    profile = selected_profile()
    settings = profile["processing"]
    if settings["artificial_air_rms_fraction"] != 0:
        raise ValueError("The selected clean profile must keep synthetic aspiration disabled.")
    report = json.loads((OUT / "comparison.json").read_text())
    original_entry = next(c for c in report["candidates"] if c["name"] == "v6-balanced-match")
    source = load(report["source"])
    reference = load(report["reference"])
    target, ref_detail = analyze(reference)
    before, _ = analyze(source)
    x = pitch_match(source, target, before, 1., micro_gain=settings["micro_gain"])
    pitch_metrics, pitch_detail = analyze(x)
    ratio = target["pitch_median_hz"] / pitch_metrics["pitch_median_hz"]
    if abs(np.log2(ratio)) > .015:
        adjusted = dict(pitch_metrics)
        for key in ["pitch_p10_hz", "pitch_p25_hz", "pitch_median_hz", "pitch_p75_hz", "pitch_p90_hz"]:
            adjusted[key] *= ratio
        x = pitch_match(x, adjusted, pitch_metrics, 1.)
        _, pitch_detail = analyze(x)
    x, pace = pace_match(x, ref_detail, pitch_detail, len(source) / RATE, OUT, 1.)
    _, detail = analyze(x)
    iterations = settings["selected_iterations"]
    if iterations != original_entry["processing"]["selected_iteration"]:
        raise ValueError("Profile iteration count differs from the approved V6 recipe.")
    print("Replaying original V6 for a deterministic differential check", flush=True)
    reproduced, _ = process(air_layer(x, detail, .12), target, ref_detail, iterations)
    original, rate = sf.read(OUT / "v6-balanced-match.wav")
    if rate != RATE or len(original) != len(reproduced):
        raise ValueError("Original V6 replay changed timing; stop before changing the recipe.")
    replay_max_error = float(np.max(np.abs(original - reproduced)))
    if replay_max_error > 2e-6:
        raise ValueError(f"Original V6 replay differs by {replay_max_error}; investigate before cleanup.")
    print(f"Original replay verified: max sample difference {replay_max_error:.2g}", flush=True)
    print("Rebuilding with artificial aspiration disabled", flush=True)
    cleaned, history = process(x, target, ref_detail, iterations)
    path = OUT / "v6-clean.wav"
    save(path, cleaned)
    metrics, _ = analyze(cleaned)
    before_metrics, _ = analyze(original)
    note = {"selected_by_user": "V6", "source": str(OUT / "v6-balanced-match.wav"),
            "output": str(path), "original_replay_max_sample_error": replay_max_error,
            "same_pitch_and_timing_input": True, "same_output_frames": len(original) == len(cleaned),
            "artificial_air_rms_fraction_before": .12, "artificial_air_rms_fraction_after": 0,
            "processing": {"micro_gain": settings["micro_gain"], "iterations": iterations, "history": history, **pace},
            "before_metrics": before_metrics, "after_metrics": metrics,
            "limitation": "Added aspiration removed at source. Perceived crackle and other resynthesis artifacts require a listening check."}
    path.with_suffix(".json").write_text(json.dumps(note, indent=2), encoding="utf-8")
    print(f"Saved {path}", flush=True)
    return path


if __name__ == "__main__":
    rebuild_v6()
