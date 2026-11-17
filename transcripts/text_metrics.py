"""Transparent text/caption statistics. Not a sleep-efficacy or literary-quality score."""
import collections
import json
import re
from pathlib import Path

import numpy as np

TOKEN = re.compile(r"\b[A-Za-z]+(?:['’][A-Za-z]+)*\b")
SENSES = {
    "sight": "light lights glow glowing candle candles window windows silver golden amber dark darkness star stars moon moonlight gleam shimmer shadow shadows",
    "sound": "sound sounds whisper whispered whispering rustle rustling footsteps voice voices hum humming murmur murmured crackle quiet silence silent softly",
    "touch": "warm warmth cool cold soft softness smooth rough damp wool velvet blanket gentle gently touch touched fingers hands",
    "smell": "smell smelled scent scented fragrance fragrant aroma aromas",
    "taste": "taste tasted sweet sweetness honey tea bread butter cinnamon apple apples chocolate"
}
PRONOUNS = {"first": "i me my mine we us our ours", "second": "you your yours yourself yourselves",
            "third": "he him his she her hers they them their theirs himself herself themselves"}
SCENIC = set("rain light candle candles window windows moon moonlight fire fireplace hearth warm warmth quiet silence gentle softly softly silver night evening castle stone book books page pages".split())


def tokens(text):
    return [w.lower().replace("’", "'") for w in TOKEN.findall(text)]


def sentences(text):
    text = re.sub(r"\b(Mr|Mrs|Ms|Dr|Prof|St)\.", r"\1<dot>", text)
    parts = re.split(r"(?<=[.!?])(?:[\"”’])?\s+", re.sub(r"\s+", " ", text).strip())
    return [s.replace("<dot>", ".") for s in parts if len(tokens(s)) >= 2]


def q(values, percentile):
    return float(np.percentile(values, percentile)) if len(values) else None


def caption_rows(path):
    """Ignore display-only newline events; deduplicate exact repeated timed fragments."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows, seen = [], set()
    ignored = 0
    for event in data.get("events", []):
        for segment in event.get("segs", []):
            text = segment.get("utf8", "").strip()
            if not text or re.fullmatch(r"\[(?:music|applause|laughter|silence)\]", text, re.I):
                ignored += 1
                continue
            start = event.get("tStartMs", 0) + segment.get("tOffsetMs", 0)
            key = (start, text)
            if key in seen:
                ignored += 1
                continue
            seen.add(key)
            rows.append({"start_seconds": start / 1000, "text": text,
                         "caption_display_end_seconds": (event.get("tStartMs", 0) + event.get("dDurationMs", 0)) / 1000})
    return rows, ignored


def measure(text):
    words = tokens(text)
    n = len(words)
    if n < 20:
        raise ValueError("Not enough text to measure")
    count = collections.Counter(words)
    sents = sentences(text)
    lengths = [len(tokens(s)) for s in sents]
    openings = collections.Counter(" ".join(tokens(s)[:2]) for s in sents)
    grams = [tuple(words[i:i + 8]) for i in range(max(0, n - 7))]
    repeated = collections.Counter(grams)
    mattr = [len(set(words[i:i + 100])) / 100 for i in range(0, n - 99, 20)]
    result = {
        "word_count": n, "sentence_count_estimate": len(sents),
        "sentence_words_p10": q(lengths, 10), "sentence_words_median": q(lengths, 50),
        "sentence_words_p90": q(lengths, 90), "sentence_words_p95": q(lengths, 95),
        "sentence_words_max": max(lengths, default=0),
        "sentences_over_40_fraction": float(np.mean(np.array(lengths) > 40)),
        "sentences_under_8_fraction": float(np.mean(np.array(lengths) < 8)),
        "question_sentence_fraction": sum("?" in s for s in sents) / max(len(sents), 1),
        "sentence_opening_top_bigram_fraction": max(openings.values(), default=0) / max(len(sents), 1),
        "mattr_100": float(np.mean(mattr)) if mattr else None,
        "repeated_8gram_token_fraction": sum(c - 1 for c in repeated.values()) / max(len(grams), 1),
        "scenic_cues_per_1000": sum(count[w] for w in SCENIC) / n * 1000,
        "dialogue_tag_cues_per_1000": sum(count[w] for w in "say says said ask asks asked reply replies replied answer answers answered whisper whispers whispered murmur murmurs murmured".split()) / n * 1000,
        "past_auxiliary_cues_per_1000": sum(count[w] for w in "was were had did".split()) / n * 1000,
        "present_auxiliary_cues_per_1000": sum(count[w] for w in "is are has have does do".split()) / n * 1000,
    }
    for group, forms in PRONOUNS.items():
        result[f"{group}_person_pronouns_per_1000"] = sum(count[w] for w in forms.split()) / n * 1000
    for sense, forms in SENSES.items():
        result[f"{sense}_cues_per_1000"] = sum(count[w] for w in set(forms.split())) / n * 1000
    return result


def windows(text, size=1000):
    # Sentence-aligned samples near 1,000 words; no invented paragraph boundaries.
    pieces, current, total = [], [], 0
    for sentence in sentences(text):
        current.append(sentence)
        total += len(tokens(sentence))
        if total >= size:
            pieces.append(" ".join(current))
            current, total = [], 0
    if total >= size * .6:
        pieces.append(" ".join(current))
    return pieces
