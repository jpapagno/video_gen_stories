"""Render prepared text using one pinned speaker reference across resumable chunks."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from .speaker import load_profile, model_fingerprint, clone_prompt


os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[1]


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
    parser.add_argument("--chunk-words", type=int, default=90, help="Maximum words per resumable chunk")
    parser.add_argument("--preview-chunks", type=int, help="Render only the first N chunks")
    parser.add_argument("--plan-only", action="store_true", help="Check text/chunking without loading the model")
    args = parser.parse_args()
    profile = load_profile(args.profile)
    if not 10 <= args.chunk_words <= 180:
        parser.error("--chunk-words must be between 10 and 180")
    text = args.input.read_text(encoding="utf-8")
    parts = chunks(text, limit=args.chunk_words)
    if args.preview_chunks is not None:
        if args.preview_chunks < 1:
            parser.error("--preview-chunks must be positive")
        parts = parts[:args.preview_chunks]
    if not parts:
        parser.error("Input contains no narration text")
    print(f"{len(parts)} chunks; {sum(len(p.split()) for p in parts)} words", flush=True)
    print(f"Voice profile: {args.profile} ({profile['display_name']}); fixed-reference cloning", flush=True)
    if args.plan_only:
        return
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable in this Python environment; use .venv-qwen")
    fingerprint = model_fingerprint(profile)
    recipe = {"workflow": "fixed-speaker-v1", "chunks": parts, "profile": profile,
              "selected_profile": args.profile, "model": profile["model"], "model_fingerprint": fingerprint,
              "max_new_tokens": 2200, "temperature": .7, "top_p": .9, "seed": 42,
              "non_streaming_mode": True,
              "note": "One pinned speaker prompt reused for every chunk; expression may still vary."}
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
    prompt = clone_prompt(model, profile, fingerprint)
    rate = None
    for number, part in enumerate(parts, 1):
        path = cache / f"{number:04d}.wav"
        if path.exists():
            continue
        print(f"Rendering {number}/{len(parts)}", flush=True)
        torch.manual_seed(recipe["seed"])
        with torch.inference_mode():
            wavs, rate = model.generate_voice_clone(text=part, language="English", voice_clone_prompt=prompt,
                non_streaming_mode=True, max_new_tokens=recipe["max_new_tokens"],
                do_sample=True, top_p=recipe["top_p"], temperature=recipe["temperature"])
        samples = np.asarray(wavs[0], dtype=np.float32)
        if not samples.size or not np.isfinite(samples).all():
            raise ValueError(f"Invalid audio in chunk {number}")
        # Stop on output near the codec-token cap rather than silently joining a likely cutoff.
        if len(samples) / rate >= 180:
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
    args.out.with_suffix(".json").write_text(json.dumps({"status": "complete", "recipe": recipe,
        "audio_seconds": sf.info(args.out).duration, "chunk_cache": str(cache)}, indent=2), encoding="utf-8")
    print(f"Saved {args.out.resolve()} ({sf.info(args.out).duration / 60:.1f} minutes)", flush=True)


if __name__ == "__main__":
    main()
