# Layered sleep-scene animation

## Create the source image

Use the included `assets/scenes/lemon-balm/greenhouse.png` for a first render. For new artwork, give your preferred image-generation tool a prompt such as:

```text
Create a cinematic 16:9 illustration for a calming bedtime story video:
a quiet greenhouse at night, blue rainy window panes in the background,
a small warm lantern near the right side, foreground ferns at lower left,
soft low-contrast light, painterly detail and a peaceful atmosphere.
Locked wide composition, no people, lettering or watermark.
Keep the lantern and foliage visually distinct for subtle animation.
```

Save the result as PNG. Match the location and mood to your story. Image generation is a manual step; this module animates an existing image. Thumbnail artwork is created separately in [packaging](../video_packaging/README.md).

## Configure another scene

Copy `animation/scenes/lemon-balm.json` to a new scene JSON. Set `image` to your project-relative PNG path and `output` to a new MP4 path. The renderer scales and centre-crops the source image to fill the frame.

| Setting | Purpose |
| --- | --- |
| `width`, `height` | Positive even output dimensions |
| `fps`, `seconds` | Frame rate and loop length; more frames cost more time |
| `rain_drops`, `rain_strength` | Rain amount and intensity |
| `lantern_centre` | Light position `[x, y]` as fractions from top left |
| `fern_region` | Foliage `[left, top, right, bottom]` as image fractions |
| `fern_sway_pixels` | Motion amplitude |
| `seed` | Procedural random variation |

Rain masking also depends on greenhouse geometry in `layers.py`; adapt that code for different architecture. First render a short low-resolution test with a copied preset, inspect moving edges and loop joins, then render the final loop to a new filename. Pass the silent MP4 to [assembly](../video_assembly/README.md).

Return to the [overview](../README.md).

This module turns a generated still into a final silent MP4. It owns animation only; story creation, voice generation and source-image generation remain separate.

```powershell
.\.venv\Scripts\python.exe -m animation animation/scenes/lemon-balm.json
.\.venv\Scripts\python.exe -m unittest animation.test_layers
```

The greenhouse preset renders 20 seconds at 1920×1080, 24 fps, using a locked camera. Moving rain is masked to blue window areas, a local flame and amber glow animate at the lantern, and selected foreground fern pixels sway slightly. These are procedural layers over the original image, not generative video. Rain already painted into the source remains visible beneath the moving layer.

Every effect is periodic, so the next loop continues from the previous one. The renderer checks that phases zero and one are pixel-identical before encoding. Video compression can still introduce tiny differences. Frame phases exclude the duplicate endpoint to avoid a pause on repetition.

Outputs are the final MP4, a JSON receipt with source hash/settings/timing, and an encoder log. Existing final MP4s are preserved: choose a new `output` in the scene JSON for another render. All compositing and encoding runs on CPU with two encoder threads; no model download, API request or GPU inference occurs. Runtime dependencies: numpy, scipy, imageio-ffmpeg (already available in this project's `.venv`).

For another scene, copy the JSON, select a source image/output, and adjust lantern coordinates and foliage region. Coordinates are fractions of image width/height. The greenhouse glass mask in `layers.py` is scene-specific and should be adapted for different architecture. This preset does not automatically segment arbitrary artwork.
