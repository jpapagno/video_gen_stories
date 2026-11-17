"""Measure three comparable creator uploads; derive provisional house-style ranges."""
import json
import hashlib
from pathlib import Path

import numpy as np

from . import ROOT, HOME
from .text_metrics import caption_rows, measure, tokens, windows

SOURCES = [
    {"id": "gryffindor", "video_id": "DqE40ZHyF7E", "title": "A Day at Hogwarts: Gryffindor Students' Adventures",
     "caption_file": "media/sleep-reference.en.json3", "video_seconds": 16905},
    {"id": "library", "video_id": "l9K6lfAX8v0", "title": "The Midnight Library Sessions: Books & Quiet Magic",
     "caption_file": "media/transcript-research/library.en.json3", "video_seconds": 16516},
    {"id": "kitchen", "video_id": "r5K09zDkTMs", "title": "The Kitchen's Secret Hours: Midnight Comfort & Magic",
     "caption_file": "media/transcript-research/kitchen.en.json3", "video_seconds": 16957}
]


def main():
    measured, sampled = [], []
    for source in SOURCES:
        rows, ignored = caption_rows(ROOT / source["caption_file"])
        if not rows:
            raise ValueError("Missing caption text")
        last = max(r["caption_display_end_seconds"] for r in rows)
        # Provisional front/back-matter exclusion, explicitly not a semantic chapter detector.
        body = [r for r in rows if 120 <= r["start_seconds"] < last - 30]
        text = " ".join(r["text"] for r in body)
        features = measure(text)
        chunks = [measure(w) for w in windows(text)]
        sampled.extend(chunks)
        bins = []
        for start in range(120, int(last - 30) - 60, 60):
            words = sum(len(tokens(r["text"])) for r in rows if start <= r["start_seconds"] < start + 60)
            if words:
                bins.append(words)
        measured.append({**source, "url": "https://www.youtube.com/watch?v=" + source["video_id"],
                         "caption_sha256": hashlib.sha256((ROOT / source["caption_file"]).read_bytes()).hexdigest(),
                         "creator": "The Sleepy Shack", "text_origin": "YouTube automatic English captions",
                         "punctuation_origin": "automatic captions; estimates, not verified author punctuation",
                         "paragraph_origin": "unavailable; caption line breaks are display events",
                         "ignored_display_or_duplicate_fragments": ignored,
                         "last_caption_display_end_seconds": last,
                         "uncaptioned_tail_seconds": source["video_seconds"] - last,
                         "measured_body_seconds": [120, last - 30], "features": features,
                         "estimated_wpm_60s_bins": {"median": float(np.median(bins)), "p10": float(np.percentile(bins, 10)), "p90": float(np.percentile(bins, 90))},
                         "windows": chunks})
    profile = {}
    excluded = {"word_count", "sentence_count_estimate", "sentence_words_max"}
    for key in sampled[0]:
        values = [m[key] for m in sampled if m[key] is not None]
        if key not in excluded:
            profile[key] = {"p10": float(np.percentile(values, 10)), "median": float(np.median(values)), "p90": float(np.percentile(values, 90))}
    folder = HOME / "research"
    folder.mkdir(exist_ok=True)
    report = {"sample_size_uploads": 3, "creators": 1, "scope": "provisional Sleepy Shack quiet-story house style, not an industry norm",
              "window_count": len(sampled), "window_words": "approximately 1000, sentence aligned",
              "sources": measured, "profile": profile,
              "limitations": ["Windows from the same three uploads are correlated, not 62 independent creator samples.",
                              "Automatic punctuation affects sentence statistics.",
                              "No paragraph-length target can be inferred from captions.",
                              "Lexicon cue counts are transparent proxies, not verified semantic labels.",
                              "Past/present auxiliary counts are not a tense classifier; dialogue affects them.",
                              "Caption absence is not by itself proof that speech ends.",
                              "Metric resemblance is not evidence of originality, coherence or sleep efficacy."]}
    (folder / "reference-measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Reference transcript measurements", "", "Three quiet-story uploads from one creator, The Sleepy Shack. This is a provisional house-style profile, not a universal sleep-story standard. Full reference prose is not reproduced here.", "",
             "Automatic caption punctuation supplies estimated sentences; caption line breaks do not supply paragraphs. The first 120 and last 30 captioned seconds are excluded provisionally, not through semantic intro detection.", "",
             "| Reference | Story-window words | Sentence median / p90 | Median estimated WPM | Last caption | Video duration |",
             "|---|---:|---:|---:|---:|---:|"]
    for s in measured:
        f = s["features"]
        lines.append(f"| [{s['title']}]({s['url']}) | {f['word_count']} | {f['sentence_words_median']:.1f} / {f['sentence_words_p90']:.1f} | {s['estimated_wpm_60s_bins']['median']:.0f} | {s['last_caption_display_end_seconds']/60:.1f} min | {s['video_seconds']/60:.1f} min |")
    lines += ["", "## Approximately 1,000-word windows", "", f"{len(sampled)} windows. These are descriptive ranges to guide a test, not pass/fail evidence of good prose.", "",
              "| Metric | 10th percentile | Median | 90th percentile |", "|---|---:|---:|---:|"]
    for key, value in profile.items():
        lines.append(f"| {key} | {value['p10']:.3f} | {value['median']:.3f} | {value['p90']:.3f} |")
    lines += ["", "Lexicon cue counts depend on a small explicit dictionary in `text_metrics.py`; they cannot establish sensory depth, dialogue share, emotional arousal or plot quality. No paragraph, new-character or scene-change counts are claimed. First-occurrence vocabulary decline is not treated as proof of declining novelty.", "",
              "Long runtimes can contain uncaptained sections. The sparse late-audio probe results for the user's reference are stored in ignored `media/transcript-research/reference-metadata.json`; do not generalize three probes to the entire tail."]
    (folder / "reference-measurements.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"sources": [{"id": s["id"], "words": s["features"]["word_count"], "median_sentence": s["features"]["sentence_words_median"], "p90_sentence": s["features"]["sentence_words_p90"], "third_pronouns_per_1000": s["features"]["third_person_pronouns_per_1000"]} for s in measured], "windows": len(sampled), "profile": profile}, indent=2))


if __name__ == "__main__":
    main()
