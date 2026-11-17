import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import speaker


class SpeakerTests(unittest.TestCase):
    def test_reference_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "voice/profiles").mkdir(parents=True)
            reference = root / "reference.wav"
            reference.write_bytes(b"fixed reference")
            profile = {"engine": "voice_clone", "reference_text": "Exact words.",
                       "reference_audio": "reference.wav",
                       "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest()}
            (root / "voice/profiles/test.json").write_text(json.dumps(profile))
            with patch.object(speaker, "ROOT", root):
                self.assertEqual(speaker.load_profile("test"), profile)
                reference.write_bytes(b"another speaker")
                with self.assertRaisesRegex(ValueError, "Reference audio changed"):
                    speaker.load_profile("test")

    def test_design_profiles_cannot_enter_narration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "voice/profiles").mkdir(parents=True)
            (root / "voice/profiles/old.json").write_text('[{"instruction":"A voice"}]')
            with patch.object(speaker, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "audition-only"):
                    speaker.load_profile("old")
