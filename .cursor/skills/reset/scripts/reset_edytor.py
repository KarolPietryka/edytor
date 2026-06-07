#!/usr/bin/env python3
"""Wrapper — deleguje do launcher/reset.py (kompatybilność ze skill reset)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from launcher.reset import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
