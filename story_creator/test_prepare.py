import unittest

from .prepare import prepare_text, prepare_file
from voice.narrate import chunks
import tempfile
from pathlib import Path


class SpeechTextTests(unittest.TestCase):
    def test_known_saint_and_titles(self):
        self.assertEqual(prepare_text("St. Jude’s welcomes Mr. Thorne and Dr. Vale."),
                         "Saint Jude’s welcomes Mister Thorne and Doctor Vale.")

    def test_ambiguous_street_and_punctuation_preserved(self):
        self.assertEqual(prepare_text("Meet at Oak St. at 3.5. Rest now!"),
                         "Meet at Oak St. at three point five. Rest now!")

    def test_british_title_without_period(self):
        self.assertEqual(prepare_text("Mrs Wren met Mrs. Bell."), "Missus Wren met Missus Bell.")

    def test_dates_times_and_numbers(self):
        self.assertEqual(prepare_text("November 6. November 8. Room 42 at 3:15."),
                         "November the sixth. November the eighth. Room forty-two at quarter past three.")
        self.assertEqual(prepare_text("6 November, 1,200 lamps, 21st, -0.5 and 25%."),
                         "the sixth of November, one thousand two hundred lamps, twenty-first, minus zero point five and twenty-five per cent.")

    def test_formatting_and_unchanged_names(self):
        self.assertEqual(prepare_text("# Title\n\n*Elian’s hearthlight.*\n\n***\n\nA chrysanthemum."),
                         "Elian’s hearthlight.\n\n\n\nA chrysanthemum.")

    def test_chunk_boundary_cannot_separate_expanded_title(self):
        self.assertEqual(chunks(prepare_text("We visit St. Jude’s. Then rest."), limit=5),
                         ["We visit Saint Jude’s.", "Then rest."])

    def test_file_stage_preserves_raw_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw.txt"
            fixed = Path(directory) / "fixed.txt"
            raw.write_text("St. Jude’s", encoding="utf-8")
            prepare_file(raw, fixed)
            self.assertEqual(raw.read_text(encoding="utf-8"), "St. Jude’s")
            self.assertEqual(fixed.read_text(encoding="utf-8"), "Saint Jude’s\n")
            with self.assertRaises(FileExistsError):
                prepare_file(raw, fixed)


if __name__ == "__main__":
    unittest.main()
