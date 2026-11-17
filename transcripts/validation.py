"""Fast editorial checks. Warnings are review aids, not proof of story quality."""
import collections
import re


def words(text):
    return re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text.lower())


def validate(text, *, minimum=600, maximum=900, accepted_texts=(), forbidden_names=(), viewpoint="third"):
    tokens = words(text)
    errors, warnings = [], []
    if not minimum <= len(tokens) <= maximum:
        errors.append(f"Word count {len(tokens)} is outside {minimum}–{maximum}.")
    if re.search(r"<think>|</think>|^\s*#{1,6}\s|^\s*(here is|here's)\b", text, re.I | re.M):
        errors.append("Output contains possible reasoning, a heading, or an introductory wrapper.")
    prose = re.sub(r"(?m)^\s*#{1,6}[^\n]*\n?", "", text)
    sentences = [" ".join(words(s)) for s in re.split(r"(?<=[.!?])\s+", prose) if len(words(s)) >= 7]
    duplicates = [s for s, count in collections.Counter(sentences).items() if count > 1]
    if duplicates:
        errors.append("Repeated complete sentences: " + " | ".join(s[:120] for s in duplicates[:3]))
    lengths = [len(words(s)) for s in re.split(r"(?<=[.!?])\s+", prose) if words(s)]
    if lengths and max(lengths) > 80:
        errors.append(f"Run-on sentence of {max(lengths)} words; revise for read-aloud clarity.")
    elif lengths and max(lengths) > 45:
        warnings.append(f"Long sentence of {max(lengths)} words; inspect read-aloud rhythm.")
    for name in forbidden_names:
        if re.search(r"\b" + re.escape(name) + r"\b", text, re.I):
            errors.append(f"Scene-boundary violation: {name} appears before their planned entrance.")
    if viewpoint == "second" and tokens.count("you") + tokens.count("your") < 5:
        warnings.append("Little second-person narration detected; inspect viewpoint.")
    if viewpoint == "third" and sum(tokens.count(w) for w in ("he", "his", "him", "she", "her", "they", "their", "rowan")) < 5:
        warnings.append("Little third-person narration detected; inspect viewpoint.")
    candidates = collections.Counter(tuple(tokens[i:i + 10]) for i in range(max(0, len(tokens) - 9)))
    repeated = [(" ".join(k), n) for k, n in candidates.items() if n > 1]
    if repeated:
        warnings.append("Repeated 10-word phrases: " + " | ".join(k for k, _ in repeated[:3]))
    prior = set()
    for accepted in accepted_texts:
        old = words(accepted)
        prior.update(tuple(old[i:i + 12]) for i in range(max(0, len(old) - 11)))
    overlap = [" ".join(tokens[i:i + 12]) for i in range(max(0, len(tokens) - 11)) if tuple(tokens[i:i + 12]) in prior]
    if overlap:
        warnings.append("Possible copied passage from an accepted scene: " + overlap[0])
    comfort = {w: tokens.count(w) for w in ["soft", "softly", "gentle", "gently", "warm", "quiet", "quietly", "settle", "settles"]}
    for word, count in comfort.items():
        if count > max(5, len(tokens) / 100):
            warnings.append(f"Frequent comfort word '{word}': {count}; inspect for vague repetition.")
    names = [name for name in ["Harry", "Hermione", "Dumbledore", "Voldemort", "Draco"] if re.search(r"\b" + name + r"\b", text)]
    if names:
        warnings.append("Unplanned canon-character references: " + ", ".join(names))
    return {"word_count": len(tokens), "longest_sentence_words": max(lengths, default=0), "hard_checks_pass": not errors, "errors": errors,
            "warnings": warnings, "comfort_word_counts": comfort,
            "status": "needs_human_review", "note": "Automated checks cannot establish continuity, required-beat coverage or literary quality."}
