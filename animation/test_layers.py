import json
import unittest
from pathlib import Path

import numpy as np

from .layers import SceneLayers


class LayerTests(unittest.TestCase):
    def setUp(self):
        config = json.loads((Path(__file__).parent / "scenes/lemon-balm.json").read_text())
        rng = np.random.default_rng(2)
        self.base = rng.integers(20, 120, (180, 320, 3), dtype=np.uint8)
        self.layers = SceneLayers(self.base, config)

    def test_periodic_layers_match_at_loop_boundary(self):
        np.testing.assert_array_equal(self.layers.frame(0), self.layers.frame(1))
        self.assertGreater(np.abs(self.layers.frame(.31).astype(float) - self.layers.frame(0)).mean(), .01)

    def test_unanimated_bench_region_remains_locked(self):
        frame = self.layers.frame(.31)
        np.testing.assert_array_equal(frame[150:170, 140:220], self.base[150:170, 140:220])


if __name__ == "__main__":
    unittest.main()
