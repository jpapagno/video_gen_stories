import wave


def wav_duration(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def build_timeline(story, chapter_audio):
    cursor = 0.0
    scenes = []
    for chapter, audio in zip(story["chapters"], chapter_audio, strict=True):
        duration = wav_duration(audio)
        scenes.append({"chapter_id": chapter["id"], "title": chapter["title"],
                       "start_seconds": round(cursor, 6),
                       "end_seconds": round(cursor + duration, 6),
                       "audio": audio.name, **chapter["scene"]})
        cursor += duration
    minimum = max(10800, story.get("target_minimum_seconds", 10800))
    return {"title": story["title"], "kind": story["kind"],
            "duration_seconds": cursor, "minimum_seconds": minimum,
            "meets_full_episode_minimum": cursor >= minimum,
            "timing_status": "measured PCM WAV frames", "scenes": scenes}


def join_wavs(paths, output):
    if not paths:
        raise ValueError("No audio to join.")
    with wave.open(str(paths[0]), "rb") as first:
        parameters = first.getparams()
    with wave.open(str(output), "wb") as dest:
        dest.setparams(parameters)
        for path in paths:
            with wave.open(str(path), "rb") as source:
                if source.getparams()[:3] != parameters[:3]:
                    raise ValueError("Incompatible WAV formats.")
                while frames := source.readframes(65536):
                    dest.writeframes(frames)
