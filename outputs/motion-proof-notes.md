# Motion proof v1

15 seconds, 1280x720, 24 fps, H.264/AAC. Audio uses seconds 12–27 of the documented St. Louis Blues transfer. A detected beat selects the cut near 6.5 seconds into the excerpt. This is a timing experiment, not a manually verified lyric alignment.

Wide shot camera push, window-side rain overlay, local lamp flicker, close-up and a localized alternate facial cel. The actress is otherwise held: no body rig, phoneme lip sync, or full pose animation. Rendered in Python/OpenCV and FFmpeg, not Three.js. Frames from wide and close-up were visually inspected; full file decoded successfully.

Alternate facial artwork made using the built-in image generator. Prompt: Preserve exact image dimensions, three panel boundaries, composition, all backgrounds, character identity, face position, linework, palette and microphone. Change ONLY the singer's face in the MIDDLE panel: gently close both eyes and part her lips slightly as if softly singing a sustained blues note. Keep head angle and silhouette exactly unchanged. All other pixels and panels should remain unchanged. This is an alternate expression cel for animation, not a redesign.

Assets: public/art/blues-storyboard-v1.png and public/art/blues-expression-v1.png. Renderer: scripts/render_proof.py. The expression edit is restricted with a soft face mask; generated changes outside it are not used.
