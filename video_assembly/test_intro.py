import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from .__main__ import ROOT, intro_settings, main


def silence(path, seconds):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\0\0" * round(24000 * seconds))


class IntroTests(unittest.TestCase):
    def test_explicit_opt_out_has_no_timing_shift(self):
        self.assertEqual(intro_settings({"intro": None})["story_start_seconds"], 0)

    def test_encoded_video_contains_intro_pause_and_body(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            silence(folder / "intro.wav", .5)
            silence(folder / "story.wav", .7)
            from voice.collection import join_stories
            join_stories([("Test story", folder / "story.wav")], folder / "body.wav")
            config = {"video": str(ROOT / "outputs/animation/lemon-balm/greenhouse-loop.mp4"),
                      "audio": str(folder / "body.wav"), "output": str(folder / "final.mp4"),
                      "intro": str(folder / "intro.wav"), "intro_lead_seconds": .2,
                      "intro_pause_seconds": .3}
            preset = folder / "preset.json"
            preset.write_text(json.dumps(config))
            with patch("sys.argv", ["video_assembly", str(preset)]):
                main()
            manifest = json.loads((folder / "final.json").read_text())
            self.assertAlmostEqual(manifest["intro"]["story_start_seconds"], 1)
            self.assertLess(abs(manifest["duration_seconds"] - 1.7), .25)
            self.assertTrue(manifest["features"]["settling_intro"])
            self.assertEqual(manifest["body_narration_seconds"], .7)
            self.assertEqual(manifest["chapters"]["chapters"][1]["timestamp"], "0:01")
            self.assertIn("0:01 Test story", (folder / "description.txt").read_text(encoding="utf-8"))
