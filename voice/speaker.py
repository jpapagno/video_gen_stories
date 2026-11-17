"""Fixed speaker profiles and reusable clone conditioning. No inference on import."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def load_profile(name):
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ValueError("Profile must be a saved lowercase profile name")
    profile = json.loads((ROOT / "voice/profiles" / f"{name}.json").read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or profile.get("engine") != "voice_clone":
        raise ValueError("Narration requires a fixed voice_clone profile; VoiceDesign is audition-only")
    if not profile.get("reference_text", "").strip():
        raise ValueError("The exact reference transcript is required")
    reference = ROOT / profile["reference_audio"]
    if sha256(reference) != profile["reference_sha256"]:
        raise ValueError("Reference audio changed; refusing to silently change speaker identity")
    return profile


def model_fingerprint(profile):
    folder = ROOT / profile["model"]
    return {name: sha256(folder / name) for name in ("config.json", "download-manifest.json")}


def clone_prompt(model, profile, fingerprint):
    """Cache only tensor/dict data; never load arbitrary pickled prompt objects."""
    import torch
    from dataclasses import asdict
    from qwen_tts.inference.qwen3_tts_model import VoiceClonePromptItem
    identity = {"profile": profile, "model_fingerprint": fingerprint, "format": 1}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    path = ROOT / "media/qwen/speaker-prompts" / f"{key}.pt"
    if path.exists():
        entries = torch.load(path, map_location="cpu", weights_only=True)
        device = model.device
        items = [VoiceClonePromptItem(**{k: v.to(device) if isinstance(v, torch.Tensor) else v
                                       for k, v in entry.items()}) for entry in entries]
        print("Loaded saved fixed speaker prompt", flush=True)
        return items
    with torch.inference_mode():
        items = model.create_voice_clone_prompt(ref_audio=str(ROOT / profile["reference_audio"]),
            ref_text=profile["reference_text"], x_vector_only_mode=False)
    entries = [{k: v.detach().cpu() if isinstance(v, torch.Tensor) else v
                for k, v in asdict(item).items()} for item in items]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".partial.pt")
    torch.save(entries, temporary)
    temporary.replace(path)
    print("Created and saved fixed speaker prompt", flush=True)
    return items
