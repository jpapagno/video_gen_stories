# Local Qwen voice audition

The audition uses the official `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` model. It designs a synthetic soft British male narrator from a text description, without cloning a real speaker. This is inference, not model training.

Environment: `.venv-qwen`, Python 3.12, separate from the Kokoro/music environment. Model weights and tokenizer: `media/qwen/VoiceDesign`. Outputs: `outputs/sleep-story/qwen`. These directories are ignored by Git.

Setup on this Windows RTX 2060 machine:

```powershell
uv venv .venv-qwen --python 3.12
uv pip install --python .venv-qwen/Scripts/python.exe torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu130
uv pip install --python .venv-qwen/Scripts/python.exe qwen-tts==0.1.1
.venv-qwen\Scripts\python scripts/download_qwen.py
.venv-qwen\Scripts\python scripts/qwen_voice_demo.py
```

The renderer forces offline Hugging Face loading after downloads. CUDA float16 and PyTorch SDPA are used; FlashAttention 2 and bfloat16 are not suitable defaults for this RTX 2060. Output includes WAV and a JSON record of exact text, voice instructions, seed, timing, and settings. A fixed seed is for repeatability, not a guarantee of identical output across hardware or runtime versions. This is a short audition, not the full story or a three-hour episode.

The resumable downloader uses official Hugging Face HTTP URLs, retains completed 8 MB chunks, and verifies model-file SHA256 hashes against repository metadata. Its chunk cache can be retained for retries. An ordinary `huggingface_hub.snapshot_download` is also supported by the upstream model, but was slow/stalled on this connection.

The script supports `--device cpu`, but full-precision CPU generation will be substantially slower and use more system memory. No hosted speech API or ElevenLabs call is part of this workflow.

Official setup and voice-design API: https://github.com/QwenLM/Qwen3-TTS

Model and Apache-2.0 license: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign

## Verified local audition

Generated on the RTX 2060 Max-Q, CUDA float16 with SDPA. Output: `outputs/sleep-story/qwen/british-bedtime-demo.wav`, 16.96 seconds, 24 kHz mono. Model loading plus synthesis took 91.23 seconds (Python import startup is additional). Peak GPU usage observed was about 5.8 GB including desktop applications. This hardware is sufficient for a short audition but has little GPU memory headroom; long-form production needs chunking and a reusable reference voice workflow. The current script only generates the short audition.

Both downloaded safetensors files passed SHA256 verification against Hugging Face metadata. The completed WAV passed decoding, non-silence, finite-sample, and clipping checks. Listening quality and accent should be judged from the demo. SoX/FlashAttention import warnings did not prevent this generation; neither is used by this audition path.
