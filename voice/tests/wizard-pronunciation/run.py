"""Isolated wizard-voice pronunciation test; wait for the main GPU job to release VRAM."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from story_creator.prepare import prepare_text

OUT = Path(__file__).resolve().parent
RAW = ("At St. Jude's, Mr. Thorne welcomed Dr. Vale into the quiet library. "
       "Elara Vance had arrived from Whistlewick at 3:15, carrying the key to Room 42. "
       "The old ledger was dated 1842. Beside it lay a sprig of star-anise and a drawing "
       "of a night-blooming cereus. Outside, the rain softened, and the lamps glowed along Oak St.")
# Explicit readings for ambiguous numbers and the street in this test; no phonetic guesses for invented names.
FIXED = prepare_text(RAW).replace("3:15", "quarter past three").replace("Room 42", "Room forty-two").replace("1842", "eighteen forty-two").replace("Oak St.", "Oak Street.")
for name, text in (("raw", RAW), ("fixed", FIXED)):
    (OUT / f"{name}.txt").write_text(text + "\n", encoding="utf-8")

while True:
    result = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True)
    used = int(result.stdout.splitlines()[0])
    if used < 1000:
        break
    print(f"Waiting for main GPU workload to release VRAM ({used} MiB used)", flush=True)
    time.sleep(15)

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

profile = json.loads((ROOT / "voice/profiles/v6-source.json").read_text(encoding="utf-8"))[0]
torch.set_num_threads(4)
print("Loading wizard voice", flush=True)
model = Qwen3TTSModel.from_pretrained(str(ROOT / "media/qwen/VoiceDesign"), device_map="cuda:0", dtype=torch.float16, attn_implementation="sdpa", local_files_only=True)
model.model.speech_tokenizer.model.to(device="cpu", dtype=torch.float32)
model.model.speech_tokenizer.device = torch.device("cpu")
torch.cuda.empty_cache()
for name, text in (("raw", RAW), ("fixed", FIXED)):
    path = OUT / f"wizard-{name}.wav"
    if path.exists():
        raise FileExistsError(path)
    print(f"Generating {name}", flush=True)
    start = time.monotonic()
    torch.manual_seed(profile["seed"])
    with torch.inference_mode():
        wavs, rate = model.generate_voice_design(text=text, language="English", instruct=profile["instruction"], max_new_tokens=1500, do_sample=True, top_p=.9, temperature=.8)
    samples = np.asarray(wavs[0], dtype=np.float32)
    if not samples.size or not np.isfinite(samples).all():
        raise ValueError("Invalid audio")
    peak = float(np.max(np.abs(samples)))
    if peak > .95:
        samples *= .95 / peak
    sf.write(path, samples, rate, subtype="PCM_16")
    path.with_suffix(".json").write_text(json.dumps({"voice": "Wizard voice", "source": profile, "text": text, "seconds": len(samples)/rate, "generation_seconds": time.monotonic()-start, "sample_rate": rate, "note": "Raw VoiceDesign. Same seed/direction; changed text can also alter prosody and identity. No V6 cleanup."}, indent=2), encoding="utf-8")
    print(f"Saved {path}", flush=True)
