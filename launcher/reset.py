"""Zabija procesy edytora i uruchamia stack od nowa."""

import sys
from pathlib import Path

from launcher.bootstrap import resolve_root
from launcher.start import main as start_main
from launcher.system_state import kill_edytor_processes, system_md_path


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    root = resolve_root(argv)
    extra = [arg for arg in argv[1:] if arg == "--debug"]

    from launcher.paths import is_frozen
    if not is_frozen() and not (root / "backend" / "server.py").exists():
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

    print("Starting stack...")
    return start_main([str(root), *extra])


if __name__ == "__main__":
    raise SystemExit(main())
