"""Offline checks for context, continuity gates and repetition detection."""
import unittest

from .pipeline import benchmark, build_prompt, read_json
from .validation import validate
from . import HOME


class PipelineTests(unittest.TestCase):
    def test_plan_has_full_word_budget_and_unique_scenes(self):
        data = read_json(HOME / "outline.json")
        scenes = [s for c in data["chapters"] for s in c["scenes"]]
        self.assertEqual(len(scenes), 36)
        self.assertEqual(len({s["id"] for s in scenes}), 36)
        self.assertGreaterEqual(sum(s["target_words"] for s in scenes), 26000)

    def test_scene_context_and_variant_are_distinct(self):
        case = benchmark("ending")
        a, p = build_prompt(case["scene_id"], "a", case)
        b, p2 = build_prompt(case["scene_id"], "b", case)
        self.assertNotEqual(a, b)
        self.assertEqual(p, p2)
        self.assertIn("No one else is present", p)
        self.assertIn("There is no next scene", p)

    def test_missing_prior_acceptance_blocks_production(self):
        with self.assertRaisesRegex(ValueError, "Prior scenes"):
            build_prompt("ch02-s01")

    def test_wrong_benchmark_context_is_rejected(self):
        with self.assertRaises(ValueError):
            build_prompt("ch01-s01", case=benchmark("ending"))

    def test_repeated_sentence_and_wrappers_are_caught(self):
        sentence = "You take the little brush and lay it carefully beside the bottle."
        result = validate("# Draft\n" + sentence + " " + sentence, minimum=1)
        self.assertFalse(result["hard_checks_pass"])
        self.assertTrue(any("Repeated complete" in e for e in result["errors"]))

    def test_copied_accepted_passage_is_flagged(self):
        text = "You take the little brush and lay it carefully beside the bottle."
        result = validate(text, minimum=1, accepted_texts=[text])
        self.assertTrue(any("copied passage" in w for w in result["warnings"]))

    def test_runon_and_early_character_entrance_are_caught(self):
        text = "Elian " + " ".join(["walks"] * 90) + "."
        result = validate(text, minimum=1, forbidden_names=["Elian"])
        self.assertFalse(result["hard_checks_pass"])
        self.assertTrue(any("Run-on" in e for e in result["errors"]))
        self.assertTrue(any("Scene-boundary" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
