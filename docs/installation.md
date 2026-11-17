# Installation

## Requirements

Use Windows PowerShell and Python 3.13 (the existing project environment uses 3.13.5), Git, and enough disk space for several GB of model files plus generated audio/video. The narration runner requires a CUDA-capable NVIDIA GPU and a compatible driver; memory use depends on hardware and input. Other modules can run without a GPU. Node.js/npm are optional and only needed for the old browser preview.

Clone this repository using its GitHub **Code** URL, then `cd` into the cloned folder. Run all following commands there. No environment activation is necessary.

## CPU tools

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements-production.txt
.venv\Scripts\python -m story_creator.prepare --help
.venv\Scripts\python -m voice profile
```

`requirements-production.txt` installs only the numerical/compositing and FFmpeg wrapper dependencies for this workflow. `imageio-ffmpeg` supplies the encoder binary; system FFmpeg is not required by these modules. The root `requirements.txt` is for the older measurement experiments. For optional voice analysis/cleanup, install `voice/requirements-analysis.txt`; those commands also need their original reference artifacts.

## Voice inference environment

```powershell
py -3.13 -m venv .venv-qwen
.venv-qwen\Scripts\python -m pip install --upgrade pip
.venv-qwen\Scripts\python -m pip install torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu130
.venv-qwen\Scripts\python -m pip install -r voice/requirements-qwen.txt
.venv-qwen\Scripts\python -c "import torch; print(torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

These are the project's saved CUDA 13.0 package versions. If wheels or your driver are incompatible, consult the [official PyTorch installer](https://pytorch.org/get-started/locally/) before choosing a different build. `CUDA available: False` means the full narration runner cannot run in that environment; check the interpreter and GPU driver before rendering.

Download the official [Qwen3-TTS 1.7B Base cloning model](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base):

```powershell
.venv\Scripts\python -m voice download
```

This uses the standard library, saves to `media/qwen/Base`, resumes partial tensor downloads and checks published LFS SHA256 hashes. It downloads the model repository's current `main` and records metadata in `download-manifest.json`; it is not pinned to an immutable revision. Keep that manifest if you need to track your exact download. Inference uses local files and does not automatically fetch missing assets. The saved synthetic Wizard reference is included under `assets/voices/wizard/`; its profile verifies the audio hash. VoiceDesign is optional and only needed to design a different voice (`python -m voice download-design`).

## Optional browser preview

```powershell
npm ci
npm run dev
```

Open the printed local URL. The old preview expects separately supplied audio at `public/media/st-louis-blues.mp3`; see [legacy notes](legacy-music-video.md). This preview is not required to export sleep-story videos.

## Troubleshooting

- Missing module: run the matching install command with the same environment's Python used to run the module.
- Missing `media/qwen/Base`: finish the explicit model download before inference.
- Out of GPU memory: close other GPU applications; the runner already decodes on CPU. There is no supported CPU mode for full `voice narrate`.
- Existing output: choose a new filename. Narration, animation, assembly, preparation and packaging preserve finished outputs.
- Missing historical WAV or report: skip `voice rebuild` and use the fresh-clone audition/narration route in the voice guide.
