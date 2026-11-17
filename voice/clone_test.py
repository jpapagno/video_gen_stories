"""Compare fixed-reference chunks with a single continuous local synthesis."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASSAGES = [
    "Neville set the last pot beside the window. Beyond the glass, the rain had softened to a whisper. He brushed a lemon balm leaf with his thumb, and its familiar scent rose gently into the warm room.",
    "Hermione closed her book and accepted a cup of tea. For once, there was nothing that needed answering before morning. The fire settled behind the grate, and they listened together to the quiet sounds of the castle.",
    "Later, Neville drew the curtains and turned down the bed. The little plant was where he had wanted it. He rested his head on the pillow, let his shoulders ease, and listened until the last note of the clock had faded."
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-model", action="store_true")
    args = parser.parse_args()
    if args.download_model:
        from .download import install
        print("Downloading and verifying Qwen 1.7B Base before the test", flush=True)
        install("base")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    profile = json.loads((ROOT / "voice/profiles/wizard-locked.json").read_text(encoding="utf-8"))
    reference = ROOT / profile["reference_audio"]
    if hashlib.sha256(reference.read_bytes()).hexdigest() != profile["reference_sha256"]:
        raise ValueError("Wizard reference changed; refusing to silently change the voice")
    recipe = {"profile": profile, "passages": PASSAGES, "seed": 42,
              "model": "media/qwen/Base", "max_new_tokens": 2200,
              "temperature": .7, "top_p": .9, "non_streaming_mode": True}
    digest = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:12]
    out = ROOT / "outputs/voice/clone-test" / digest
    out.mkdir(parents=True, exist_ok=True)
    (out / "recipe.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    print(f"Test outputs: {out}", flush=True)
    torch.set_num_threads(4)
    model = Qwen3TTSModel.from_pretrained(str(ROOT / recipe["model"]), device_map="cuda:0",
        dtype=torch.float16, attn_implementation="sdpa", local_files_only=True)
    model.model.speech_tokenizer.model.to(device="cpu", dtype=torch.float32)
    model.model.speech_tokenizer.device = torch.device("cpu")
    torch.cuda.empty_cache()
    with torch.inference_mode():
        prompt = model.create_voice_clone_prompt(ref_audio=str(reference),
            ref_text=profile["reference_text"], x_vector_only_mode=False)
    print("Built fixed speaker prompt once; reusing it for all four requests", flush=True)
    receipts = []
    for label, text in [(f"chunk-{n}", text) for n, text in enumerate(PASSAGES, 1)] + [("one-go", " ".join(PASSAGES))]:
        path = out / f"{label}.wav"
        metadata = path.with_suffix(".json")
        if path.exists() and metadata.exists():
            receipts.append(json.loads(metadata.read_text(encoding="utf-8")))
            continue
        print(f"Generating {label}", flush=True)
        torch.manual_seed(42)
        started = time.monotonic()
        with torch.inference_mode():
            wavs, rate = model.generate_voice_clone(text=text, language="English", voice_clone_prompt=prompt,
                non_streaming_mode=True, max_new_tokens=2200, do_sample=True, temperature=.7, top_p=.9)
        samples = np.asarray(wavs[0], dtype=np.float32)
        if not samples.size or not np.isfinite(samples).all():
            raise ValueError(f"Invalid audio: {label}")
        if len(samples) / rate > 180:
            raise RuntimeError("Output near generation cap; possible cutoff")
        peak = float(np.max(np.abs(samples)))
        if peak > .95:
            samples *= .95 / peak
        sf.write(path, samples, rate, subtype="PCM_16")
        receipt = {"label": label, "text": text, "audio_seconds": len(samples) / rate,
                   "generation_seconds": time.monotonic() - started,
                   "reference_sha256": profile["reference_sha256"]}
        metadata.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        receipts.append(receipt)
        print(json.dumps(receipt), flush=True)
    joined = []
    for number in range(1, 4):
        samples, rate = sf.read(out / f"chunk-{number}.wav", dtype="float32")
        if joined:
            joined.append(np.zeros(round(.6 * rate), np.float32))
        joined.append(samples)
    sf.write(out / "separate-chunks.wav", np.concatenate(joined), rate, subtype="PCM_16")
    (out / "result.json").write_text(json.dumps({"status": "complete", "renders": receipts,
        "review": "Listen for identity, accent, pace, missing words and joins. Fixed reference is not a guarantee of identical prosody."}, indent=2), encoding="utf-8")
    print("Comparison complete: separate-chunks.wav and one-go.wav", flush=True)


if __name__ == "__main__":
    main()
