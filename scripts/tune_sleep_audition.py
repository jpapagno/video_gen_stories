"""Compatibility launcher; implementation lives in voice/tuning.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == "__main__":
    import runpy
    runpy.run_module("voice.tuning", run_name="__main__")
else:
    from voice.tuning import *
