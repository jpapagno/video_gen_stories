"""Build versioned scene prompts, preserve local drafts, and request explicit editorial reviews."""
import hashlib
import json
import re
from pathlib import Path

from . import HOME, ROOT
from . import client
from .validation import validate


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def scene(scene_id):
    for chapter in read_json(HOME / "outline.json")["chapters"]:
        for item in chapter["scenes"]:
            if item["id"] == scene_id:
                return {**item, "chapter_title": chapter["title"], "chapter_purpose": chapter["purpose"]}
    raise ValueError(f"Unknown scene: {scene_id}")


def benchmark(case_id):
    for case in read_json(HOME / "benchmark.json")["cases"]:
        if case["id"] == case_id:
            return case
    raise ValueError(f"Unknown benchmark case: {case_id}")


def build_prompt(scene_id, variant="a", case=None):
    if variant not in ("a", "b"):
        raise ValueError("Prompt variant must be a or b")
    brief = scene(scene_id)
    state = read_json(HOME / "continuity.json")
    if case:
        if case["scene_id"] != scene_id:
            raise ValueError("Benchmark context belongs to a different scene.")
        context = {"benchmark_context": True, "facts": case["facts"],
                   "previous_ending": case["previous_ending"], "next_scene": case["next_scene"]}
    else:
        accepted = state["accepted_scene_ids"]
        outline = read_json(HOME / "outline.json")
        ordered = [s["id"] for c in outline["chapters"] for s in c["scenes"]]
        prior = ordered[:ordered.index(scene_id)]
        if any(item not in accepted for item in prior):
            raise ValueError("Prior scenes are not accepted. Use an isolated benchmark case or review continuity before continuing.")
        context = state
    summary = [{"id": c["id"], "title": c["title"], "purpose": c["purpose"]}
               for c in read_json(HOME / "outline.json")["chapters"]]
    system = (HOME / f"prompts/scene-{variant}.md").read_text(encoding="utf-8")
    prompt = "\n\n".join(["STORY BIBLE\n" + (HOME / "story-bible.md").read_text(encoding="utf-8"),
                           "EPISODE DIRECTION\n" + json.dumps(summary, ensure_ascii=False),
                           "CURRENT SCENE\n" + json.dumps(brief, ensure_ascii=False),
                           "CONTINUITY AND HANDOFF\n" + json.dumps(context, ensure_ascii=False),
                           "Write only this scene, approximately 750 words. End at its required handoff."])
    return system, prompt


def model_snapshot():
    cfg = client.config()
    tag = next((m for m in client.get("/api/tags")["models"] if m["name"] == cfg["model"]), None)
    if tag is None:
        raise ValueError(f"Model {cfg['model']} is not installed locally. Run the pull command first.")
    return {"tag": tag["name"], "digest": tag["digest"], "details": tag.get("details"),
            "runtime": client.get("/api/version")}


def draft(scene_id, variant="a", case=None):
    cfg = client.config()
    system, prompt = build_prompt(scene_id, variant, case)
    snapshot = model_snapshot()
    recipe = {"system": system, "prompt": prompt, "config": cfg, "model": snapshot,
              "workflow_version": 1, "scene_id": scene_id, "prompt_variant": variant,
              "benchmark_case": case["id"] if case else None}
    digest = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
    folder = HOME / "drafts" / f"{scene_id}-{variant}-{digest[:12]}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "story.txt"
    if path.exists() and (folder / "generation.json").exists() and (folder / "checks.json").exists():
        print(f"Reusing saved draft: {path}", flush=True)
        return path
    (folder / "prompt.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    print(f"Drafting {scene_id}, prompt {variant.upper()} locally", flush=True)
    text, event = client.generate(system, prompt, partial_path=folder / "story.partial.txt")
    path.write_text(text + "\n", encoding="utf-8")
    event.pop("response", None)
    event.pop("thinking", None)
    event.pop("context", None)
    event["prompt_sha256"] = digest
    (folder / "generation.json").write_text(json.dumps(event, indent=2), encoding="utf-8")
    check = validate(text, minimum=cfg["minimum_scene_words"], maximum=cfg["maximum_scene_words"],
                     accepted_texts=[p.read_text(encoding="utf-8") for p in (HOME / "chapters").glob("*.txt")])
    if event.get("done_reason") == "length":
        check["errors"].append("Generation hit its token limit; inspect for truncation.")
        check["hard_checks_pass"] = False
    (folder / "checks.json").write_text(json.dumps(check, indent=2), encoding="utf-8")
    print(f"Saved {check['word_count']} words; checks {'pass' if check['hard_checks_pass'] else 'need revision'}: {path}", flush=True)
    return path


def review(path):
    path = Path(path).resolve()
    recipe = read_json(path.parent / "prompt.json")
    system = (HOME / "prompts/review.md").read_text(encoding="utf-8")
    prompt = recipe["prompt"] + "\n\nAUTOMATED CHECKS\n" + (path.parent / "checks.json").read_text(encoding="utf-8")
    prompt += "\n\nDRAFT TO REVIEW\n" + path.read_text(encoding="utf-8")
    print(f"Reviewing {path.parent.name} locally", flush=True)
    text, event = client.generate(system, prompt, options={"temperature": .2, "num_predict": 1500},
                                  format="json", partial_path=path.parent / "review.partial.txt")
    try:
        result = json.loads(text)
        required = {"read_aloud", "specificity", "gentle_movement", "continuity", "sleep_tone", "freshness"}
        if set(result.get("scores", {})) != required:
            raise ValueError("Review did not contain the six rubric scores")
        if not all(isinstance(v, (int, float)) and 0 <= v <= 4 for v in result["scores"].values()):
            raise ValueError("Review score outside 0–4")
        result["unverified_evidence"] = [i.get("evidence", "") for i in result.get("issues", [])
                                         if i.get("evidence") and i["evidence"] not in path.read_text(encoding="utf-8")]
    except (json.JSONDecodeError, ValueError) as error:
        result = {"review_error": str(error), "raw_review": text}
    result["status"] = "local_editorial_estimate_needs_human_review"
    result["done_reason"] = event.get("done_reason")
    (path.parent / "review.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def revise(path):
    path = Path(path).resolve()
    recipe = read_json(path.parent / "prompt.json")
    check = read_json(path.parent / "checks.json")
    review_path = path.parent / "review.json"
    findings = read_json(review_path) if review_path.exists() else {}
    notes_path = path.parent / "editor-notes.json"
    editorial_notes = read_json(notes_path) if notes_path.exists() else {}
    system = (HOME / "prompts/revise.md").read_text(encoding="utf-8")
    prompt = recipe["prompt"] + "\n\nORIGINAL DRAFT\n" + path.read_text(encoding="utf-8")
    prompt += "\n\nFINDINGS\n" + json.dumps({"checks": check, "local_model_review": findings,
                                              "specific_editorial_notes": editorial_notes})
    cfg = client.config()
    snapshot = model_snapshot()
    revision_recipe = {"system": system, "prompt": prompt, "config": cfg, "model": snapshot, "workflow_version": 2}
    key = hashlib.sha256(json.dumps(revision_recipe, sort_keys=True).encode()).hexdigest()[:12]
    target = path.parent / f"revision-{key}.txt"
    if target.exists():
        return target
    text, event = client.generate(system, prompt, partial_path=target.with_suffix(".partial.txt"))
    target.write_text(text + "\n", encoding="utf-8")
    case_id = recipe.get("benchmark_case")
    forbidden = ["Elian"] if case_id == "arrival" else []
    result = {"source": str(path), "checks": validate(text, forbidden_names=forbidden), "done_reason": event.get("done_reason"),
              "system_prompt": system, "prompt": prompt, "model": snapshot, "config": cfg}
    if event.get("done_reason") == "length":
        result["checks"]["hard_checks_pass"] = False
        result["checks"]["errors"].append("Revision hit its token limit; inspect for truncation.")
    target.with_suffix(".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return target
