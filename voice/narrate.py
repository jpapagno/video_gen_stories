"""Render a text file in short VoiceDesign chunks. Raw voice, not V6 cleanup."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path


os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[1]


def load_profile(name):
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ValueError("Profile must be a saved lowercase profile name")
    path = ROOT / "voice/profiles" / f"{name}.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(profile, dict) and "source_profile" in profile:
        source = (ROOT / profile["source_profile"]).resolve()
        if not source.is_relative_to((ROOT / "voice/profiles").resolve()):
            raise ValueError("Source profile must remain inside voice/profiles")
        variants = json.loads(source.read_text(encoding="utf-8"))
        return next(v for v in variants if v["name"] == profile["source_variant"])
    if isinstance(profile, list) and len(profile) == 1:
        return profile[0]
    raise ValueError("Profile must name a VoiceDesign source variant")


def chunks(text, limit=90):
    text = text.strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result, current = [], []
    for sentence in sentences:
        words = sentence.split()
        # Bound unusually long sentences as well as ordinary paragraphs.
        for start in range(0, len(words), limit):
            piece = words[start:start + limit]
            if current and len(current) + len(piece) > limit:
                result.append(" ".join(current))
                current = []
            current.extend(piece)
    if current:
        result.append(" ".join(current))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", default="wizard", help="Saved voice profile (default: wizard)")
    parser.add_argument("--preview-chunks", type=int, help="Render only the first N chunks")
    parser.add_argument("--plan-only", action="store_true", help="Check text/chunking without loading the model")
    args = parser.parse_args()
    profile = load_profile(args.profile)
    text = args.input.read_text(encoding="utf-8")
    parts = chunks(text)
    if args.preview_chunks is not None:
        if args.preview_chunks < 1:
            parser.error("--preview-chunks must be positive")
        parts = parts[:args.preview_chunks]
    if not parts:
        parser.error("Input contains no narration text")
    print(f"{len(parts)} chunks; {sum(len(p.split()) for p in parts)} words", flush=True)
    print(f"Voice profile: {args.profile} ({profile['name']})", flush=True)
    if args.plan_only:
        return
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable in this Python environment; use .venv-qwen")
    recipe = {"chunks": parts, "profile": profile, "selected_profile": args.profile, "model": "media/qwen/VoiceDesign",
              "max_new_tokens": 1500, "temperature": .8, "top_p": .9,
              "note": "Raw VoiceDesign with saved source direction; independent chunks may vary in identity. V6 audition cleanup is not applied."}
    key = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:12]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cache = args.out.parent / (args.out.stem + "-chunks-" + key)
    cache.mkdir(exist_ok=True)
    (cache / "recipe.json").write_text(json.dumps(recipe, indent=2), encoding="utf-8")
    (cache / "spoken-text.txt").write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    if args.out.exists():
        raise FileExistsError(f"Output already exists: {args.out}; choose another --out")
    torch.set_num_threads(4)
    model = Qwen3TTSModel.from_pretrained(str(ROOT / recipe["model"]), device_map="cuda:0",
        dtype=torch.float16, attn_implementation="sdpa", local_files_only=True)
    model.model.speech_tokenizer.model.to(device="cpu", dtype=torch.float32)
    model.model.speech_tokenizer.device = torch.device("cpu")
    torch.cuda.empty_cache()
    rate = None
    for number, part in enumerate(parts, 1):
        path = cache / f"{number:04d}.wav"
        if path.exists():
            continue
        print(f"Rendering {number}/{len(parts)}", flush=True)
        torch.manual_seed(profile.get("seed", 42))
        with torch.inference_mode():
            wavs, rate = model.generate_voice_design(text=part, language="English",
                instruct=profile["instruction"], max_new_tokens=1500,
                do_sample=True, top_p=.9, temperature=.8)
        samples = np.asarray(wavs[0], dtype=np.float32)
        if not samples.size or not np.isfinite(samples).all():
            raise ValueError(f"Invalid audio in chunk {number}")
        # Stop on output near the codec-token cap rather than silently joining a likely cutoff.
        if len(samples) / rate >= 123:
            raise RuntimeError(f"Chunk {number} may have hit the token cap; split its text further")
        peak = float(np.max(np.abs(samples)))
        if peak > .95:
            samples *= .95 / peak
        temp = path.with_suffix(".partial.wav")
        sf.write(temp, samples, rate, subtype="PCM_16")
        temp.replace(path)
    temp = args.out.with_suffix(".partial.wav")
    rate = sf.info(cache / "0001.wav").samplerate
    with sf.SoundFile(temp, "w", samplerate=rate, channels=1, subtype="PCM_16", format="WAV") as sink:
        for number in range(1, len(parts) + 1):
            samples, chunk_rate = sf.read(cache / f"{number:04d}.wav", dtype="float32")
            if chunk_rate != rate or samples.ndim != 1:
                raise ValueError("Inconsistent chunk audio")
            sink.write(samples)
            if number < len(parts):
                sink.write(np.zeros(round(.6 * rate), dtype=np.float32))
    temp.replace(args.out)
    print(f"Saved {args.out.resolve()} ({sf.info(args.out).duration / 60:.1f} minutes)", flush=True)


if __name__ == "__main__":
    main()
