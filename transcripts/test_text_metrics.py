import json
import tempfile
import unittest
from pathlib import Path

from .text_metrics import caption_rows, measure, sentences


class TextMetricTests(unittest.TestCase):
    def test_caption_display_breaks_do_not_create_sentences(self):
        data = {"events": [{"tStartMs": 0, "dDurationMs": 2000, "segs": [{"utf8": "He opens"}]},
                           {"tStartMs": 500, "segs": [{"utf8": "\n"}]},
                           {"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "the door."}]}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.json"
            path.write_text(json.dumps(data))
            rows, ignored = caption_rows(path)
        self.assertEqual(len(sentences(" ".join(r["text"] for r in rows))), 1)
        self.assertEqual(ignored, 1)

    def test_exact_duplicate_timed_fragment_is_removed(self):
        event = {"tStartMs": 0, "segs": [{"utf8": "The door."}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.json"
            path.write_text(json.dumps({"events": [event, event]}))
            rows, ignored = caption_rows(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(ignored, 1)

    def test_abbreviation_is_not_a_sentence_boundary(self):
        self.assertEqual(len(sentences("Mr. Vale opens the cabinet. Rowan watches him.")), 2)

    def test_metrics_do_not_claim_paragraphs_or_semantic_quality(self):
        text = "Rowan opens the cabinet and finds a little brush beside a folded cloth. He places the brush on the table."
        result = measure(text)
        self.assertGreater(result["third_person_pronouns_per_1000"], 0)
        self.assertNotIn("paragraph_length", result)
        self.assertNotIn("quality_score", result)


if __name__ == "__main__":
    unittest.main()
