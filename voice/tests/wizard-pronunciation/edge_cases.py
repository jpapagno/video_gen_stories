"""Generate isolated, labelled pronunciation probes without changing story prose."""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

CASES = [
    ("01-mrs-original", "Mrs Wren", "That looks like Mrs Wren’s writing. She kept the household spells before you."),
    ("02-mrs-expanded", "Missus Wren", "That looks like Missus Wren’s writing. She kept the household spells before you."),
    ("03-dates-original", "Numeric dates", "November 6. Blue hearthlight returned to west passage. November 8. Ada says she could see it from the bend."),
    ("04-dates-expanded", "Spoken dates", "November the sixth. Blue hearthlight returned to west passage. November the eighth. Ada says she could see it from the bend."),
    ("05-bow-original", "Key bow", "Mara turned the key over in her palm. It had a round bow, a short stem and three uneven teeth."),
    ("06-bow-reworded", "Key loop", "Mara turned the key over in her palm. It had a round loop, a short stem and three uneven teeth."),
    ("07-names", "Names", "Mara Bell worked at Alderwick School. Tamsin Vale was the cook. Elian Reed tended the greenhouse. Ivo Pell kept the library."),
    ("08-hearthlight-compound", "Hearthlight compound", "My mother called that sort of flame a hearthlight. They used to be common round here."),
    ("09-hearth-light-spaced", "Hearth light spaced", "My mother called that sort of flame a hearth light. They used to be common round here."),
    ("10-chrysanthemum", "Chrysanthemum", "They had tea and apple cake. Elian brought in a late chrysanthemum in a narrow jar."),
    ("11-format-original", "Raw emphasis and scene break", "*Ask Elian about the colour.*\n\n***\n\nElian Reed worked in the school greenhouse, where November was permitted to enter only as far as the porch."),
    ("12-format-cleaned", "Clean emphasis and scene break", "Ask Elian about the colour.\n\nElian Reed worked in the school greenhouse, where November was permitted to enter only as far as the porch."),
    ("13-dialogue", "Short dialogue turns", "“Well, warmth wakes it. But it needs to borrow its colour.”\n\n“From what?”\n\n“Something particular to the place it belongs.”"),
]


def main():
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    folder = Path(__file__).resolve().parent / "edge-cases"
    folder.mkdir(exist_ok=True)
    profile = json.loads((ROOT / "voice/profiles/v6-source.json").read_text(encoding="utf-8"))[0]
    recipe = {"voice": "Wizard voice", "source": profile, "model": "media/qwen/VoiceDesign",
              "seed": profile["seed"], "max_new_tokens": 650, "temperature": .8, "top_p": .9,
              "note": "Independent VoiceDesign clips: same direction/seed, but text changes can change identity and delivery. No V6 cleanup. No pronunciation success assumed."}
    (folder / "recipe.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    torch.set_num_threads(4)
    print("Loading local wizard voice", flush=True)
    model = Qwen3TTSModel.from_pretrained(str(ROOT / recipe["model"]), device_map="cuda:0", dtype=torch.float16, attn_implementation="sdpa", local_files_only=True)
    model.model.speech_tokenizer.model.to(device="cpu", dtype=torch.float32)
    model.model.speech_tokenizer.device = torch.device("cpu")
    torch.cuda.empty_cache()
    rows = []
    for slug, label, text in CASES:
        path = folder / f"{slug}.wav"
        if path.exists():
            rows.append(json.loads(path.with_suffix(".json").read_text(encoding="utf-8")))
            continue
        print(f"Generating {slug}", flush=True)
        start = time.monotonic()
        torch.manual_seed(profile["seed"])
        with torch.inference_mode():
            wavs, rate = model.generate_voice_design(text=text, language="English", instruct=profile["instruction"], max_new_tokens=650, do_sample=True, top_p=.9, temperature=.8)
        samples = np.asarray(wavs[0], dtype=np.float32)
        if not samples.size or not np.isfinite(samples).all():
            raise ValueError(f"Invalid audio: {slug}")
        peak = float(np.max(np.abs(samples)))
        if peak > .95:
            samples *= .95 / peak
        sf.write(path, samples, rate, subtype="PCM_16")
        row = {"slug": slug, "label": label, "text": text, "file": str(path), "seconds": len(samples)/rate, "generation_seconds": time.monotonic()-start}
        path.with_suffix(".json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        rows.append(row)
        print(f"Saved {slug}: {row['seconds']:.1f}s", flush=True)
    (folder / "index.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    rate = sf.info(rows[0]["file"]).samplerate
    position = 0.
    index = ["# Wizard voice pronunciation probes", "", "Clips are in numbered order; the combined audio has two-second gaps. These are listening probes, not verified pronunciation fixes.", ""]
    with sf.SoundFile(folder / "all-cases.wav", "w", samplerate=rate, channels=1, subtype="PCM_16") as sink:
        for row in rows:
            samples, current_rate = sf.read(row["file"], dtype="float32")
            if current_rate != rate:
                raise ValueError("Sample rates differ")
            index.extend([f"## {row['slug']} — {position:.1f}s", "", row["text"], ""])
            sink.write(samples)
            sink.write(np.zeros(2 * rate, dtype=np.float32))
            position += len(samples)/rate + 2
    (folder / "README.md").write_text("\n".join(index), encoding="utf-8")
    print(f"Completed {len(rows)} clips: {folder}", flush=True)


if __name__ == "__main__":
    main()
