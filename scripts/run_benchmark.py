"""Thin wrapper — delegates to `draftbench` Click CLI.

Run via:
    python -m scripts.run_benchmark run --cases data/mini/cases.jsonl --models claude-opus-4.7

Or use the installed entry point directly (after `pip install -e .`):
    draftbench run --cases data/mini/cases.jsonl --models claude-opus-4.7
"""

from __future__ import annotations

import sys

from draftbench.__main__ import main

if __name__ == "__main__":
    sys.exit(main() or 0)
