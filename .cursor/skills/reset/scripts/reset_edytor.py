#!/usr/bin/env python3
"""Zabija procesy z System.md i uruchamia stack od nowa (jak skill edytor)."""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EDYTOR_SCRIPTS = SCRIPT_DIR.parent.parent / "edytor" / "scripts"
sys.path.insert(0, str(EDYTOR_SCRIPTS))

from system_state import kill_edytor_processes, system_md_path  # noqa: E402


def main() -> int:
    argv = list(sys.argv[1:])
    root = Path(argv[0] if argv else ".").resolve()
    extra_args = [arg for arg in argv[1:] if arg == "--debug"]

    if not (root / "backend" / "server.py").exists():
        print(f"ERR: not edytor root: {root}", file=sys.stderr)
        return 1

    sys_path = system_md_path(root)
    if sys_path.exists():
        print(f"Reading {sys_path}")
    else:
        print("System.md not found — killing by port only")

    killed = kill_edytor_processes(root)
    if killed:
        print(f"Killed PIDs: {', '.join(str(p) for p in killed)}")
    else:
        print("No processes to kill")

    pycache = root / "backend" / "__pycache__"
    if pycache.exists():
        for pyc in pycache.glob("*.pyc"):
            pyc.unlink(missing_ok=True)

    start_script = EDYTOR_SCRIPTS / "start_edytor.py"
    print("Starting stack...")
    r = subprocess.run(
        [sys.executable, str(start_script), str(root), *extra_args],
        check=False,
    )
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
