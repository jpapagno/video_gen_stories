"""Local Qwen3-TTS synthesis and short voice-design auditions."""
import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

ROOT = Path(__file__).resolve().parents[1]
TEXT = ("Beyond the window, the rain moves softly across the lake. "
        "You settle into the comfortable chair, your hands warm around the cup. "
        "There is nothing left to finish this evening. "
        "The lamp shines gently on the page, and the castle rests around you.")
INSTRUCTION = ("A warm adult male narrator with a subtle British English accent. "
               "Soft, smooth, rounded voice without gravel or rasp. "
               "Quiet bedtime storytelling, slow unhurried phrasing, gentle sentence endings, "
               "restrained expression. Natural relaxed speech, not whispering. "
               "Speak softly and evenly, like a comforting bedtime audiobook.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=ROOT / "media/qwen/VoiceDesign")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/sleep-story/qwen")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--variants", type=Path, help="JSON list of named instruction/seed variants; load model once")
    parser.add_argument("--decoder-cpu", action="store_true", help="Free GPU memory by decoding audio on CPU")
    parser.add_argument("--max-new-tokens", type=int, default=400)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    torch.set_num_threads(4)
    dtype = torch.float16 if args.device.startswith("cuda") else torch.float32
    print(f"Loading local VoiceDesign on {args.device} ({dtype})", flush=True)
    start = time.monotonic()
    model = Qwen3TTSModel.from_pretrained(str(args.model), device_map=args.device,
                                         dtype=dtype, attn_implementation="sdpa",
                                         local_files_only=True)
    if args.decoder_cpu:
        model.model.speech_tokenizer.model.to(device="cpu", dtype=torch.float32)
        model.model.speech_tokenizer.device = torch.device("cpu")
        torch.cuda.empty_cache()
        print("Audio decoder moved to CPU; voice generation remains on GPU.", flush=True)
    variants = json.loads(args.variants.read_text(encoding="utf-8")) if args.variants else [
        {"name": "british-bedtime-demo", "instruction": INSTRUCTION, "seed": args.seed}]
    for variant in variants:
        name = variant["name"]
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
            raise ValueError("Variant names must be safe lowercase slugs.")
        target = args.out / f"{name}.wav"
        if target.exists():
            print(f"Preserving existing {target}", flush=True)
            continue
        instruction = variant["instruction"]
        seed = variant.get("seed", args.seed)
        torch.manual_seed(seed)
        print(f"Generating {name}...", flush=True)
        with torch.inference_mode():
            wavs, rate = model.generate_voice_design(text=TEXT, language="English", instruct=instruction,
                                                 max_new_tokens=args.max_new_tokens, do_sample=True,
                                                 top_p=0.9, temperature=0.8)
        samples = np.asarray(wavs[0], dtype=np.float32)
        if samples.size == 0 or not np.isfinite(samples).all():
            raise ValueError("Model returned empty or invalid audio.")
        peak = float(np.max(np.abs(samples)))
        if peak > 0.95:
            samples *= 0.95 / peak
        sf.write(target, samples, rate, subtype="PCM_16")
        metadata = {"model": str(args.model), "text": TEXT, "instruction": instruction,
                "seed": seed, "device": args.device, "dtype": str(dtype),
                "decoder_cpu": args.decoder_cpu, "max_new_tokens": args.max_new_tokens,
                "duration_seconds": len(samples) / rate, "sample_rate": rate,
                "elapsed_seconds": time.monotonic() - start, "peak_before_gain": peak,
                "hosted_speech_api_requests": 0}
        settings_name = "demo-settings.json" if not args.variants else f"{name}.json"
        (args.out / settings_name).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(json.dumps({"audio": str(target), **metadata}, indent=2), flush=True)


if __name__ == "__main__":
    main()
