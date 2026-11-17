import json
import tempfile
import unittest
import wave
from pathlib import Path

from voice.collection import join_stories
from .chapters import load_audio_chapters, export_chapters
from video_packaging.chapters import update_description


def wav(path, frames):
    with wave.open(str(path), "wb") as sink:
        sink.setnchannels(1)
        sink.setsampwidth(2)
        sink.setframerate(24000)
        sink.writeframes(b"\0\0" * frames)


class ChaptersTests(unittest.TestCase):
    def test_repeat_intro_and_pauses_produce_measured_description(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            first, second, audio = folder / "one.wav", folder / "two.wav", folder / "joined.wav"
            wav(first, 24000 * 12 + 1)
            wav(second, 24000 * 18 + 3)
            data = join_stories([("One", first), ("Two", second), ("One — repeat", first)], audio, 2)
            self.assertEqual(data["chapters"][1]["start_frame"], 24000 * 14 + 1)
            self.assertEqual(data["chapters"][2]["start_frame"], 24000 * 34 + 4)
            data = load_audio_chapters(audio)
            description = folder / "description.txt"
            description.write_text("A cosy story.\n", encoding="utf-8")
            output = folder / "final.mp4"
            result = export_chapters(output, data, {"story_start_seconds": 27.32}, description)
            self.assertAlmostEqual(result["chapters"][2]["start_seconds"], 41.3200416667)
            self.assertIn("0:41 Two", description.read_text(encoding="utf-8"))
            text = output.with_suffix(".chapters.txt").read_text(encoding="utf-8")
            update_description(description, text)
            self.assertEqual(description.read_text(encoding="utf-8").count("Chapters:"), 1)
            wav(audio, 24000)
            with self.assertRaisesRegex(ValueError, "does not match"):
                load_audio_chapters(audio)

    def test_invalid_order_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "joined.wav"
            story = Path(directory) / "one.wav"
            wav(story, 24000)
            data = join_stories([("One", story), ("Two", story)], audio, 0)
            data["chapters"][1]["start_frame"] = 0
            audio.with_suffix(".chapters.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unordered"):
                load_audio_chapters(audio)
