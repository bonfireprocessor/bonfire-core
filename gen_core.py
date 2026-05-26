#!/usr/bin/env python3
"""Compatibility wrapper for the FuseSoC core generator."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    script = Path(__file__).resolve().parent / "fusesoc-cores" / "generators" / "gen_core.py"
    runpy.run_path(str(script), run_name="__main__")
