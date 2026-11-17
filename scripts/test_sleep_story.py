"""Offline checks: never call ElevenLabs or consume credits."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sleep_story_lib.audio import generate
from sleep_story_lib.story import load_story, chunks

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.story = load_story(ROOT / "stories/hogwarts-night/prototype.json")

    def test_chunking_preserves_prose(self):
        text = ("A quiet sentence.\n\nAnother sentence follows. " * 500) + "End."
        parts = chunks(text)
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(part) <= 3500 for part in parts))

    def test_cli_requires_review_flag(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/sleep_story.py"), "generate"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--approved-script", result.stderr)

    def test_budget_guard_precedes_network(self):
        with tempfile.TemporaryDirectory() as folder, patch("sleep_story_lib.audio.request_speech") as request:
            with self.assertRaises(ValueError):
                generate(self.story, Path(folder), 1)
            request.assert_not_called()

    def test_mock_audio_cache_and_measured_scene_boundaries(self):
        # One second of silent PCM per chapter, deliberately synthetic fixture.
        response = {"audio_base64": base64.b64encode(bytes(48000)).decode(), "alignment": None}
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-only", "ELEVENLABS_VOICE_ID": "testVoice"}), patch("sleep_story_lib.audio.request_speech", return_value=response) as request:
            out = Path(folder)
            generate(self.story, out, 10000)
            count = request.call_count
            self.assertEqual(count, 3)
            timeline = json.loads((out / "timeline.json").read_text())
            self.assertEqual(timeline["duration_seconds"], 3)
            self.assertEqual([s["start_seconds"] for s in timeline["scenes"]], [0, 1, 2])
            self.assertFalse(timeline["meets_full_episode_minimum"])
            generate(self.story, out, 10000)
            self.assertEqual(request.call_count, count)
            self.story["kind"] = "episode"
            with self.assertRaisesRegex(ValueError, "under three hours"):
                generate(self.story, out, 10000)


if __name__ == "__main__":
    unittest.main()
