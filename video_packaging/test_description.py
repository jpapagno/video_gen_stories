import tempfile
import unittest
from pathlib import Path

from .description import duration_label, render_description
from .chapters import update_description


class DescriptionTests(unittest.TestCase):
    def test_runtime_does_not_overclaim_three_hours(self):
        self.assertEqual(duration_label(10800 - 1), "179 minutes")
        self.assertEqual(duration_label(11322), "3 hours")

    def test_short_copy_and_chapter_style_survive_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "description.txt"
            text = render_description(opening="Welcome to Hogwarts.", seconds=11322,
                experience="gentle narration.", synopsis="Six original, unofficial fan-created stories.",
                intro=True, hashtags=("#HarryPotter",))
            path.write_text(text, encoding="utf-8")
            chapters = "0:00 Welcome\n0:27 First story\n2:45:34 First story — repeat\n"
            update_description(path, chapters, approximate=True)
            update_description(path, chapters, approximate=True)
            result = path.read_text(encoding="utf-8")
            self.assertTrue(result.startswith("Welcome to Hogwarts. Enjoy 3 hours"))
            self.assertIn("Subscribe to SleepyStorykeeper", result)
            self.assertIn("2:45:34 First story — Part 2", result)
            self.assertEqual(result.count("Chapters (approximate story transitions):"), 1)
