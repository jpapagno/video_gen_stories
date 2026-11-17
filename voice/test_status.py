import tempfile
import unittest
import wave
from pathlib import Path

from .status import inspect


class StatusTests(unittest.TestCase):
    def test_final_audio_completes_even_when_process_has_exited(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "story.wav"
            with wave.open(str(output), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(24000)
                audio.writeframes(b"\0\0" * 24000)
            self.assertEqual(inspect(output, False)["state"], "complete")

    def test_process_exit_is_not_mistaken_for_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "story.wav"
            self.assertEqual(inspect(output, False)["state"], "stopped_incomplete")
            output.with_suffix(".stderr.log").write_text("Traceback (most recent call last)\nOOM")
            self.assertEqual(inspect(output, False)["state"], "failed")
