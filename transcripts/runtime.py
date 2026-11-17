"""Install a portable CPU-only official Ollama runtime using selective ZIP extraction."""
import hashlib
import json
import urllib.request
import zlib
from pathlib import PurePosixPath

from . import HOME

VERSION = "v0.40.16"
DEST = HOME / "runtime"


def install(vulkan=False, cuda=False):
    from remotezip import RemoteFetcher, RemoteZip
    url = f"https://api.github.com/repos/ollama/ollama/releases/tags/{VERSION}"
    with urllib.request.urlopen(url, timeout=60) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == "ollama-windows-amd64.zip")

    class KnownSizeFetcher(RemoteFetcher):
        def get_file_size(self):
            return asset["size"]

    DEST.mkdir(parents=True, exist_ok=True)
    installed = []
    with RemoteZip(asset["browser_download_url"], fetcher=KnownSizeFetcher,
                   support_suffix_range=False, timeout=120) as archive:
        for member in archive.infolist():
            parts = PurePosixPath(member.filename).parts
            if member.is_dir() or ".." in parts or PurePosixPath(member.filename).is_absolute():
                continue
            # CPU backend: omit the much larger CUDA/Vulkan backend directories.
            root_library = len(parts) == 3 and parts[:2] == ("lib", "ollama")
            vulkan_library = vulkan and len(parts) == 4 and parts[:3] == ("lib", "ollama", "vulkan")
            cuda_library = cuda and len(parts) == 4 and parts[:3] == ("lib", "ollama", "cuda_v13")
            if member.filename != "ollama.exe" and not root_library and not vulkan_library and not cuda_library:
                continue
            target = DEST.joinpath(*parts).resolve()
            if not target.is_relative_to(DEST.resolve()):
                raise ValueError("Archive path escaped runtime directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            data = target.read_bytes() if target.exists() and target.stat().st_size == member.file_size else None
            # Reuse an identical CUDA DLL from the local voice environment when available.
            candidate = HOME.parent / ".venv-qwen/Lib/site-packages/torch/lib" / parts[-1]
            if cuda_library and data is None and candidate.exists() and candidate.stat().st_size == member.file_size:
                cached = candidate.read_bytes()
                if zlib.crc32(cached) == member.CRC:
                    data = cached
                    target.write_bytes(data)
            if data is None or zlib.crc32(data) != member.CRC:
                print(f"Installing {member.filename}", flush=True)
                data = archive.read(member)  # zipfile validates the member CRC.
                temporary = target.with_suffix(target.suffix + ".partial")
                temporary.write_bytes(data)
                temporary.replace(target)
            installed.append({"file": member.filename, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (DEST / "manifest.json").write_text(json.dumps({"version": VERSION, "source": asset["browser_download_url"],
        "backend": "CPU" + (" + Vulkan" if vulkan else "") + (" + CUDA 13" if cuda else ""), "verification": "HTTPS upstream release, ZIP CRC on extracted files, local file hashes",
        "files": installed}, indent=2), encoding="utf-8")
    print("Portable runtime installed:", DEST / "ollama.exe", flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vulkan", action="store_true", help="Also install the compact optional GPU backend")
    parser.add_argument("--cuda", action="store_true", help="Also install the NVIDIA CUDA 13 backend")
    args = parser.parse_args()
    install(args.vulkan, args.cuda)
