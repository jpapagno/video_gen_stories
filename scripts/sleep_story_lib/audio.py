"""Explicit synthesis only; sequential requests, content-addressed cache, no retries."""
import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
import wave

from .story import chunks, estimate
from .timeline import join_wavs, build_timeline


def request_speech(payload, voice, key):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=pcm_24000"
    request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Avoid dumping request headers or credential-bearing objects.
        raise RuntimeError(f"ElevenLabs HTTP {error.code}. Check account, quota, voice access, and settings. No automatic retry.") from None
    except urllib.error.URLError:
        raise RuntimeError("ElevenLabs connection failed. Check connectivity; retry manually to avoid duplicate credit usage.") from None


def generate(story, out, ceiling):
    if estimate(story)["characters"] > ceiling:
        raise ValueError("Story exceeds --max-characters. No request sent.")
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise ValueError("Set ELEVENLABS_API_KEY locally in .env. No request sent.")
    voice = os.environ.get("ELEVENLABS_VOICE_ID") or story["voice_id"]
    if not voice.isalnum():
        raise ValueError("Voice ID must be alphanumeric.")
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "cache"
    cache.mkdir(exist_ok=True)
    chapter_audio = []
    jobs = [(chapter, part) for chapter in story["chapters"] for part in chunks(chapter["text"])]
    completed = {chapter["id"]: [] for chapter in story["chapters"]}
    for index, (chapter, text) in enumerate(jobs):
        payload = {"text": text, "model_id": story["model_id"], "voice_settings": story["voice_settings"]}
        if index:
            payload["previous_text"] = jobs[index - 1][1][-1000:]
        if index + 1 < len(jobs):
            payload["next_text"] = jobs[index + 1][1][:1000]
        digest = hashlib.sha256(json.dumps({"voice": voice, "format": "pcm_24000", **payload}, sort_keys=True).encode()).hexdigest()
        raw = cache / f"{digest}.json"
        if raw.exists():
            result = json.loads(raw.read_text(encoding="utf-8"))
        else:
            print(f"Synthesizing {chapter['id']} part {index + 1}/{len(jobs)} ({len(text)} characters)", flush=True)
            result = request_speech(payload, voice, key)
            # Save successful provider result before local conversion so reruns reuse it.
            temporary = raw.with_suffix(".tmp")
            temporary.write_text(json.dumps(result), encoding="utf-8")
            temporary.replace(raw)
        pcm = base64.b64decode(result["audio_base64"], validate=True)
        if not pcm or len(pcm) % 2:
            raise RuntimeError("Invalid 16-bit PCM response.")
        wav = cache / f"{digest}.wav"
        with wave.open(str(wav), "wb") as dest:
            dest.setnchannels(1)
            dest.setsampwidth(2)
            dest.setframerate(24000)
            dest.writeframes(pcm)
        alignment = {k: result.get(k) for k in ("alignment", "normalized_alignment")}
        wav.with_suffix(".alignment.json").write_text(json.dumps(alignment), encoding="utf-8")
        completed[chapter["id"]].append(wav)
    for chapter in story["chapters"]:
        path = out / f"{chapter['id']}.wav"
        join_wavs(completed[chapter["id"]], path)
        chapter_audio.append(path)
    join_wavs(chapter_audio, out / "narration.wav")
    timeline = build_timeline(story, chapter_audio)
    (out / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(f"Audio: {out / 'narration.wav'} ({timeline['duration_seconds'] / 60:.2f} minutes)")
    if story["kind"] == "episode" and not timeline["meets_full_episode_minimum"]:
        raise ValueError("Episode is under three hours. Audio saved for revision; runtime gate FAILED.")
