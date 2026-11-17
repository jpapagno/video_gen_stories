"""Independent, periodic rain, firelight and foliage layers."""
import numpy as np
from scipy.ndimage import gaussian_filter, shift


class SceneLayers:
    def __init__(self, image, config):
        self.base = image.astype(np.float32)
        self.height, self.width = image.shape[:2]
        self.config = config
        h, w = self.height, self.width
        yy, xx = np.mgrid[:h, :w]
        x, y = xx / w, yy / h
        # Rain belongs to the blue glass; warm furniture and green plants stay dry.
        blue = np.clip((self.base[:, :, 2] - self.base[:, :, 0] + 3) / 24, 0, 1)
        self.glass = blue * (x > .035) * (x < .855) * (y < .64)
        for column, half_width in ((.148, .006), (.284, .005), (.491, .006), (.632, .006), (.716, .005), (.843, .009)):
            self.glass *= (np.abs(x - column) > half_width)
        self.glass = gaussian_filter(self.glass.astype(np.float32), .7)
        rng = np.random.default_rng(config["seed"])
        count = config["rain_drops"]
        self.rain_x = rng.uniform(.025, .86, count)
        self.rain_phase = rng.random(count)
        self.rain_cycles = rng.integers(3, 10, count)
        self.rain_lengths = rng.integers(7, 23, count)
        self.rain_alpha = rng.uniform(.12, .5, count) * config["rain_strength"]
        cx, cy = config["lantern_centre"]
        self.glow_roi = (slice(int((cy - .18) * h), min(h, int((cy + .23) * h))),
                         slice(int((cx - .14) * w), min(w, int((cx + .12) * w))))
        gy, gx = np.mgrid[self.glow_roi[0], self.glow_roi[1]]
        self.gx, self.gy = gx / w - cx, gy / h - cy
        self.halo = np.exp(-((self.gx / .075) ** 2 + (self.gy / .105) ** 2) * 2)
        left, top, right, bottom = config["fern_region"]
        self.fern_roi = (slice(int(top * h), int(bottom * h)), slice(int(left * w), int(right * w)))
        self.fern = self.base[self.fern_roi].copy()
        green = np.clip((self.fern[:, :, 1] - self.fern[:, :, 0] * .88 - self.fern[:, :, 2] * .12) / 28, 0, 1)
        fh, fw = green.shape
        fy, fx = np.mgrid[:fh, :fw]
        edge = np.minimum.reduce([fx / 20, (fw - 1 - fx) / 20, fy / 20, (fh - 1 - fy) / 20, np.ones_like(fx)])
        self.fern_mask = (gaussian_filter(green, 1) * np.clip(edge, 0, 1))[:, :, None]

    def frame(self, phase):
        # Integer frequencies and modulo positions make every layer repeat exactly.
        phase = phase % 1.0
        angle = 2 * np.pi * phase
        frame = self.base.copy()
        sway = self.config["fern_sway_pixels"] * np.sin(angle)
        if abs(sway) > 1e-6:
            moved = shift(self.fern, (0, sway, 0), order=1, mode="nearest", prefilter=False)
            frame[self.fern_roi] += (moved - self.fern) * self.fern_mask

        # Light flickers locally, rather than pulsing brightness over the whole scene.
        flutter = .52 + .22 * np.sin(3 * angle) + .15 * np.sin(7 * angle + .8) + .11 * np.sin(11 * angle + 1.7)
        patch = frame[self.glow_roi]
        patch += self.halo[:, :, None] * np.array([13, 7, 1], np.float32) * flutter
        bend = .0018 * np.sin(5 * angle) + .0007 * np.sin(13 * angle)
        flame_height = .013 + .002 * np.sin(7 * angle + .5)
        flame = np.exp(-(((self.gx - bend * np.clip(-self.gy / .025, 0, 1)) / .0038) ** 2
                         + ((self.gy + .005) / flame_height) ** 2) * 1.8)
        patch += flame[:, :, None] * np.array([62, 36, 9], np.float32) * (.65 + .35 * flutter)

        # Thin falling streaks: sparse splatting at half resolution, softly blended.
        rh, rw = self.height // 2, self.width // 2
        rain = np.zeros((rh, rw), dtype=np.float32)
        positions = (self.rain_phase + phase * self.rain_cycles) % 1
        for px, py, length, alpha in zip(self.rain_x, positions, self.rain_lengths, self.rain_alpha):
            ys = (int(py * rh) - np.arange(length)) % rh
            xs = np.clip(int(px * rw) + np.arange(length) // 9, 0, rw - 1)
            np.add.at(rain, (ys, xs), alpha * np.linspace(1, .12, length))
        rain = np.repeat(np.repeat(rain, 2, axis=0), 2, axis=1)
        opacity = np.clip(rain * self.glass, 0, .55)[:, :, None]
        frame += (np.array([161, 188, 207], np.float32) - frame) * opacity
        return np.clip(frame, 0, 255).astype(np.uint8)
