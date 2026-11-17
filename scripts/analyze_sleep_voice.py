"""Compatibility launcher; implementation lives in voice/basic_analysis.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == "__main__":
    import runpy
    runpy.run_module("voice.basic_analysis", run_name="__main__")
else:
    from voice.basic_analysis import *
