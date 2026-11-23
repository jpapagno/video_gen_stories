"""Independent, periodic rain, firelight and foliage layers."""
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, shift


class LandscapeMotion:
    def __init__(self, image, polygon, effect):
        h, w = image.shape[:2]
        vertices = np.asarray(polygon) * [w, h]
        left, top = np.floor(vertices.min(axis=0)).astype(int)
        right, bottom = np.ceil(vertices.max(axis=0)).astype(int)
        self.roi = np.s_[top:bottom, left:right]
        self.patch = image[self.roi]
        self.y, self.x = np.mgrid[:bottom-top, :right-left].astype(np.float32)
        mask = np.zeros(self.x.shape, dtype=bool)
        x, y = self.x + left, self.y + top
        for (ax, ay), (bx, by) in zip(vertices, np.roll(vertices, -1, axis=0)):
            if ay != by:
                mask ^= ((ay > y) != (by > y)) & (x < ax + (y - ay) * (bx - ax) / (by - ay))
        self.mask = np.clip(distance_transform_edt(mask) / 15, 0, 1).astype(np.float32)
        self.effect = effect
        self.scale = w / 1920

    def apply(self, frame, angle):
        if self.effect == "clouds":
            dx = self.scale * (19 * np.sin(angle) + 4 * np.sin(2 * angle + self.y / 85))
            dy = 1.5 * self.scale * np.sin(angle + self.x / 105)
        else:
            depth = .4 + .6 * self.y / self.y.shape[0]
            dx = self.scale * depth * (5 * np.sin(3 * angle + self.y / 4) +
                                      2 * np.sin(5 * angle + self.x / 46 + self.y / 7))
            dy = self.scale * depth * np.sin(4 * angle + self.y / 5 + self.x / 38)
        coords = (self.y + dy * self.mask, self.x + dx * self.mask)
        patch = frame[self.roi]
        for channel in range(3):
            original = self.patch[:, :, channel]
            moved = map_coordinates(original, coords, order=1, mode="nearest", prefilter=False)
            patch[:, :, channel] += (moved - original) * self.mask


class SceneLayers:
    def __init__(self, image, config):
        self.base = image.astype(np.float32)
        self.height, self.width = image.shape[:2]
        self.config = config
        self.landscape = [LandscapeMotion(self.base, polygon, effect)
                          for effect, polygon in config.get("landscape_motion", {}).items()]
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
        for motion in self.landscape:
            motion.apply(frame, angle)
        sway = self.config["fern_sway_pixels"] * np.sin(angle)
        if abs(sway) > 1e-6:
            moved = shift(self.fern, (0, sway, 0), order=1, mode="nearest", prefilter=False)
            frame[self.fern_roi] += (moved - self.fern) * self.fern_mask

        # Light flickers locally, rather than pulsing brightness over the whole scene.
        flutter = .52 + .22 * np.sin(3 * angle) + .15 * np.sin(7 * angle + .8) + .11 * np.sin(11 * angle + 1.7)
        patch = frame[self.glow_roi]
        gain = self.config.get("lantern_flicker_gain", 1)
        patch += self.halo[:, :, None] * np.array([13, 7, 1], np.float32) * flutter * gain
        bend = .0018 * np.sin(5 * angle) + .0007 * np.sin(13 * angle)
        flame_height = .013 + .002 * np.sin(7 * angle + .5)
        flame = np.exp(-(((self.gx - bend * np.clip(-self.gy / .025, 0, 1)) / .0038) ** 2
                         + ((self.gy + .005) / flame_height) ** 2) * 1.8)
        patch += flame[:, :, None] * np.array([62, 36, 9], np.float32) * (.65 + .35 * flutter) * gain

        if not self.rain_x.size:
            return np.clip(frame, 0, 255).astype(np.uint8)

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
