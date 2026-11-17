"""A focused short-block experiment after the first long-scene prompts failed review."""
import hashlib
import json
from pathlib import Path

from . import HOME
from . import client
from .pipeline import model_snapshot
from .validation import validate

OPTIONS = {"temperature": .65, "top_p": .9, "top_k": 40, "presence_penalty": 0.,
           "repeat_penalty": 1., "num_predict": 600, "seed": 42}
BLOCKS = [
    {"id": 1, "start": "approaching the sheltered stone arch outside Hogwarts on a rainy autumn evening",
     "actions": ["Walk the last few paces beneath the arch.", "Notice how the rain sound changes beneath shelter.", "Reach the closed but unlatched wooden inner door, without opening it yet."],
     "end": "standing sheltered beside the wooden inner door, blue wool coat still worn and damp"},
    {"id": 2, "start": "standing sheltered beside the wooden inner door, coat still worn and damp",
     "actions": ["Open the unlatched door using its brass pull.", "Step into the entrance hall and let the door close gently.", "Notice the dry stone floor and a few steady floating candles."],
     "end": "just inside the entrance hall, hands still damp, coat still worn"},
    {"id": 3, "start": "just inside the entrance hall, hands damp and coat still worn",
     "actions": ["Pause and look around this ordinary welcoming space.", "Notice an umbrella stand and a wooden stool nearby.", "Discover a clean folded towel on the stool; stop before touching it."],
     "end": "inside the hall, noticing the folded towel, hands still damp and coat still worn"}
]
FACTS = ["You are an unnamed adult magical cartographer visiting Hogwarts by invitation.",
         "It is one rainy autumn evening; no thunder, danger or hurry.",
         "You wear a damp blue wool coat throughout this scene. Do not remove, hang, dry or fold it.",
         "You are alone. No named or unnamed person enters, speaks, appears or is introduced. Elian is not present.",
         "No dialogue. No key, atlas, brush, lamp, tea, luggage, personal umbrella or new magical rule.",
         "The door is wooden, closed but unlatched until block 2. It opens onto the stone entrance hall.",
         "The clean towel remains folded and untouched until the scene ends. Do not dry your hands."]


def sample():
    system = (HOME / "prompts/legacy-scene-c.md").read_text(encoding="utf-8")
    recipe = {"workflow": "focused-blocks-v1", "system": system, "facts": FACTS, "blocks": BLOCKS,
              "prompt": "LOCKED FACTS\n" + json.dumps(FACTS) + "\nPLANNED BLOCKS\n" + json.dumps(BLOCKS),
              "scene_id": "ch01-s01", "prompt_variant": "c", "benchmark_case": "arrival",
              "options": {**client.config()["options"], **OPTIONS}, "model": model_snapshot()}
    key = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:12]
    folder = HOME / "drafts" / f"ch01-s01-c-{key}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "prompt.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    pieces, problems = [], []
    for block in BLOCKS:
        path = folder / f"block-{block['id']}.txt"
        if path.exists() and path.with_suffix(".json").exists():
            text = path.read_text(encoding="utf-8").strip()
        else:
            prompt = "LOCKED FACTS\n" + json.dumps(FACTS) + "\nCURRENT BLOCK\n" + json.dumps(block)
            prompt += "\nPREVIOUS PROSE (do not repeat)\n" + "\n\n".join(pieces)[-3500:]
            prompt += "\nWrite only this block in 230–270 words. Respect its end state and stop."
            print(f"Writing focused block {block['id']}/3", flush=True)
            text, event = client.generate(system, prompt, options=OPTIONS, partial_path=path.with_suffix(".partial.txt"))
            path.write_text(text + "\n", encoding="utf-8")
            event.pop("response", None); event.pop("thinking", None); event.pop("context", None)
            path.with_suffix(".json").write_text(json.dumps({"system": system, "prompt": prompt,
                "options": OPTIONS, "generation": event}, indent=2), encoding="utf-8")
        check = validate(text, minimum=180, maximum=330, forbidden_names=["Elian"])
        block_generation = json.loads(path.with_suffix(".json").read_text())["generation"]
        if block_generation.get("done_reason") == "length":
            check["hard_checks_pass"] = False
            check["errors"].append("Block hit token limit; inspect for truncation.")
        if not check["hard_checks_pass"]:
            problems.append({"block": block["id"], "errors": check["errors"]})
        pieces.append(text)
    story = "\n\n".join(pieces)
    (folder / "story.txt").write_text(story + "\n", encoding="utf-8")
    check = validate(story, forbidden_names=["Elian"])
    check["block_problems"] = problems
    if problems:
        check["hard_checks_pass"] = False
    (folder / "checks.json").write_text(json.dumps(check, indent=2), encoding="utf-8")
    generations = [json.loads((folder / f"block-{b['id']}.json").read_text())["generation"] for b in BLOCKS]
    (folder / "generation.json").write_text(json.dumps({"mode": "focused-blocks", "blocks": generations,
        "done": True, "total_duration": sum(g.get("total_duration", 0) for g in generations)}, indent=2), encoding="utf-8")
    print(json.dumps({"file": str(folder / "story.txt"), "checks": check}, indent=2))
    return folder / "story.txt"


if __name__ == "__main__":
    sample()
