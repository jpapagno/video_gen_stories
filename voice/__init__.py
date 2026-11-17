"""Local voice generation, acoustic processing, and the selected V6 profile.

Importing this package does not load Qwen, contact the network, or start rendering.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def selected_profile():
    """Read the selected voice and its processing settings."""
    path = Path(__file__).parent / "profiles/v6-clean.json"
    return json.loads(path.read_text(encoding="utf-8"))


def rebuild_selected_voice():
    """Reproduce the approved V6 clean audition using existing local artifacts."""
    from .cleanup import rebuild_v6
    return rebuild_v6()


__all__ = ["selected_profile", "rebuild_selected_voice"]
