"""A bounded follow-up trial: short actions, explicit states, no previous prose to echo."""
import hashlib
import json

from . import HOME
from . import client
from .pipeline import model_snapshot
from .text_metrics import measure
from .validation import validate

BLOCKS = [
    {"id": 1, "state": "Rowan and Elian stand in the Hogwarts map room. Rowan holds the brass cabinet key. The cabinet is shut. On the worktable are a green-shaded lamp and Rowan's cup of apple tea.",
     "actions": "Rowan turns the key and opens the cabinet. Elian steadies the door. Rowan removes the key and places it on the table.",
     "end": "Cabinet open; key on table; both people remain standing in the room.", "objects": ["key", "cabinet", "worktable", "lamp", "tea cup"]},
    {"id": 2, "state": "The cabinet is already open and the key is on the table. A small tray of tools is on an inner shelf.",
     "actions": "Elian lifts out the tray and puts it on the worktable. It holds a closed silver ink bottle, soft brush, small brush dish, and scrap of paper.",
     "end": "Tray and unused tools on the worktable; bottle closed; Rowan watches.", "objects": ["cabinet", "tray", "ink bottle", "brush", "dish", "paper scrap", "worktable"]},
    {"id": 3, "state": "The tray of unused tools is on the table beside the green-shaded lamp. Rowan's tea cup is near the working space.",
     "actions": "Rowan moves his tea cup to one side and lays the paper scrap flat. Elian angles the lamp toward the paper.",
     "end": "Working space clear, paper flat and well lit; tools not yet used.", "objects": ["tea cup", "paper scrap", "lamp", "table", "tray"]},
    {"id": 4, "state": "The paper is flat beneath the lamp. The brush lies unused on the tray and the ink bottle is closed.",
     "actions": "Elian opens the ink bottle and sets its stopper on the tray. He tells Rowan, 'Only the tip.' Rowan picks up the brush but has not dipped it yet.",
     "end": "Ink bottle open, stopper on tray, Rowan holding the dry brush.", "objects": ["ink bottle", "stopper", "tray", "brush", "paper", "lamp"]},
    {"id": 5, "state": "Rowan holds the dry brush above the open silver ink bottle. The paper scrap is waiting beneath the lamp.",
     "actions": "Rowan touches the brush tip to the ink, then draws one thin silver line on the scrap. Elian observes and says, 'That's enough.' The line is ordinary ink, with no magical effect.",
     "end": "One plain silver line on paper; Rowan still holds the brush; bottle open.", "objects": ["brush", "ink", "bottle", "paper", "lamp"]},
    {"id": 6, "state": "The silver practice line is complete. Rowan holds the brush. The bottle stopper and small brush dish are on the tray.",
     "actions": "Rowan rests the brush in its dish and replaces the stopper. Elian gives the finished line a small acknowledging nod. End with the completed practice task; introduce no next activity.",
     "end": "Brush in dish, bottle secured, practice line on paper. Both people still in the map room.", "objects": ["brush", "dish", "tray", "bottle", "stopper", "paper"]}
]
OPTIONS = {"temperature": .6, "top_p": .9, "top_k": 40, "repeat_penalty": 1.05,
           "presence_penalty": .2, "frequency_penalty": 0., "num_predict": 300, "seed": 73}


def main():
    system = (HOME / "prompts/scene-e-state.md").read_text(encoding="utf-8")
    recipe = {"workflow": "measured-state-trial-v2", "system": system, "blocks": BLOCKS,
              "options": {**client.config()["options"], **OPTIONS}, "model": model_snapshot(),
              "note": "Same model and original scene as D; tests a bundled workflow change, not an isolated causal experiment. No reference prose or prior generated prose is provided."}
    key = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:12]
    folder = HOME / "drafts" / f"quiet-task-e-{key}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "prompt.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    parts, events = [], []
    for block in BLOCKS:
        path = folder / f"block-{block['id']}.txt"
        if path.exists() and path.with_suffix(".json").exists():
            text = path.read_text(encoding="utf-8").strip()
            event = json.loads(path.with_suffix(".json").read_text())["generation"]
        else:
            prompt = "SETTING: a dry map room at Hogwarts on a rainy autumn evening.\n" + json.dumps(block)
            prompt += "\nWrite only this action paragraph in about 90–120 words. Finish at the expected end state."
            print(f"Writing state-focused block {block['id']}/6 locally", flush=True)
            text, event = client.generate(system, prompt, options=OPTIONS, partial_path=path.with_suffix(".partial.txt"))
            for field in ("response", "thinking", "context"):
                event.pop(field, None)
            path.write_text(text + "\n", encoding="utf-8")
            path.with_suffix(".json").write_text(json.dumps({"prompt": prompt, "generation": event}, indent=2), encoding="utf-8")
        parts.append(text)
        events.append(event)
    story = "\n\n".join(parts)
    (folder / "story.txt").write_text(story + "\n", encoding="utf-8")
    features = measure(story)
    checks = validate(story, minimum=450, maximum=850, viewpoint="third")
    for term in ("student", "students", "she", "her", "hers", "oil"):
        from .text_metrics import tokens
        if term in tokens(story):
            checks["hard_checks_pass"] = False
            checks["errors"].append(f"Protected-fact flag in this two-adult-male scene: {term}")
    if any(e.get("done_reason") == "length" for e in events):
        checks["hard_checks_pass"] = False
        checks["errors"].append("One or more blocks hit their token limit.")
    result = {"file": str(folder / "story.txt"), "metrics": features, "checks": checks,
              "status": "needs_editorial_and_user_review", "elapsed_generation_seconds": sum(e.get("total_duration", 0) for e in events) / 1e9}
    (folder / "measurement.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return folder / "story.txt"


if __name__ == "__main__":
    main()
