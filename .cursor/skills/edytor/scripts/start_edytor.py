#!/usr/bin/env python3
"""Wrapper — deleguje do launcher/start.py (kompatybilność ze skill edytor)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from launcher.start import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
