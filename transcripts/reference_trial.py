"""One bounded, original, third-person quiet-task test guided by measured prose ranges."""
import hashlib
import json
from pathlib import Path

from . import HOME
from . import client
from .pipeline import model_snapshot
from .text_metrics import measure
from .validation import validate

FACTS = [
    "Rowan is an adult male visiting cartographer. Narration follows him in third person, present tense.",
    "Rowan and Elian Vale are both in the small map room at Hogwarts, above the Black Lake.",
    "It is a rainy autumn evening. The rain is outside the closed window; the room is dry.",
    "A green-shaded brass lamp and Rowan's cup of apple tea are already on the oak worktable.",
    "Rowan's blue coat is drying on its entrance-hall hook, not in this room.",
    "The brass cabinet key is in Rowan's hand at the start. The atlas cabinet is shut.",
    "The faded-blue atlas remains closed on its shelf throughout this sample.",
    "The brush, small silver ink bottle, scrap of paper and little brush dish may be handled normally.",
    "No new magic is demonstrated; this is a practical introduction to the tools. Both people stay in the room."
]
BLOCKS = [
    {"id": 1, "action": "Rowan uses the brass key to open the cabinet. Elian steadies the door. Rowan leaves the atlas on its shelf and places the key on the worktable.",
     "end_state": "Cabinet door open, atlas still closed on its shelf, key on the table. Both people are standing by the worktable."},
    {"id": 2, "action": "Elian arranges the small silver ink bottle, brush and paper scrap on the worktable. Rowan moves his tea cup a little aside to make working space. Elian adjusts the lamp toward the paper.",
     "end_state": "Tools arranged beside the lamp. Cup safely to one side. Atlas remains on its shelf. Neither person has used the brush yet."},
    {"id": 3, "action": "Elian gives one short practical instruction about using only the brush tip. Rowan dips it lightly and draws one silver line on the scrap. Elian acknowledges the result. Rowan rests the brush in its dish.",
     "end_state": "One plain silver practice line on the scrap, brush resting in dish, ink bottle on table. The cabinet is open but the atlas is still closed on its shelf. End here."}
]
OPTIONS = {"temperature": .6, "top_p": .9, "top_k": 40, "repeat_penalty": 1.,
           "presence_penalty": 0., "frequency_penalty": 0., "num_predict": 550, "seed": 73}


def main():
    system = (HOME / "prompts/scene-d-measured.md").read_text(encoding="utf-8")
    profile = json.loads((HOME / "formats/quiet-journey-v1.json").read_text())
    recipe = {"system": system, "profile": profile, "facts": FACTS, "blocks": BLOCKS,
              "options": {**client.config()["options"], **OPTIONS}, "model": model_snapshot(),
              "workflow": "measured-format-trial-v1", "copyright_boundary": "Only aggregate reference measurements and our original plot supplied; no reference story prose."}
    key = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:12]
    folder = HOME / "drafts" / f"quiet-task-d-{key}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "prompt.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    chunks, metadata = [], []
    for block in BLOCKS:
        path = folder / f"block-{block['id']}.txt"
        if path.exists() and path.with_suffix(".json").exists():
            text = path.read_text(encoding="utf-8").strip()
            event = json.loads(path.with_suffix(".json").read_text())["generation"]
        else:
            prompt = "CURRENT FACTS\n" + json.dumps(FACTS) + "\nCURRENT BLOCK\n" + json.dumps(block)
            prompt += "\nPREVIOUS PROSE (continue, do not repeat)\n" + "\n\n".join(chunks)[-3000:]
            prompt += "\nWrite only this action sequence, about 180–230 words. End at the stated end state without recapping it."
            print(f"Writing measured-format block {block['id']}/3 locally", flush=True)
            text, event = client.generate(system, prompt, options=OPTIONS, partial_path=path.with_suffix(".partial.txt"))
            for field in ("response", "thinking", "context"):
                event.pop(field, None)
            path.write_text(text + "\n", encoding="utf-8")
            path.with_suffix(".json").write_text(json.dumps({"prompt": prompt, "generation": event}, indent=2), encoding="utf-8")
        chunks.append(text)
        metadata.append(event)
    story = "\n\n".join(chunks)
    (folder / "story.txt").write_text(story + "\n", encoding="utf-8")
    features = measure(story)
    checks = validate(story, minimum=450, maximum=800, viewpoint="third")
    if any(event.get("done_reason") == "length" for event in metadata):
        checks["hard_checks_pass"] = False
        checks["errors"].append("A writing block hit its token limit; inspect for truncation.")
    comparison = {"metrics": features, "checks": checks,
                  "ranges": {k: {"draft": features[k], "guidance": limits,
                                 "inside_guidance": limits[0] <= features[k] <= limits[1]}
                             for k, limits in profile["numeric_guidance"].items()},
                  "status": "needs_editorial_and_user_review; metric resemblance is not a quality score"}
    (folder / "measurement.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps({"story": str(folder / "story.txt"), **comparison}, indent=2))
    return folder / "story.txt"


if __name__ == "__main__":
    main()
