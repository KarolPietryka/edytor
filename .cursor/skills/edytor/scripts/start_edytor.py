#!/usr/bin/env python3
"""Start edytor BE (:3000) and static FE (:8888). Idempotent-ish."""

import socket
import subprocess
import sys
from pathlib import Path


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def venv_python(root: Path) -> Path:
    win = root / ".venv" / "Scripts" / "python.exe"
    if win.exists():
        return win
    unix = root / ".venv" / "bin" / "python"
    if unix.exists():
        return unix
    return Path(sys.executable)


def start(cmd: list[str], cwd: Path) -> None:
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        cmd,
        cwd=cwd,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    py = venv_python(root)

    if not (root / "backend" / "server.py").exists():
        print(f"ERR: not edytor root: {root}", file=sys.stderr)
        return 1

    if port_open(3000):
        print("BE already on :3000")
    else:
        start([str(py), str(root / "backend" / "server.py")], root)
        print("BE started on :3000")

    if port_open(8888):
        print("FE already on :8888")
    else:
        start([str(py), "-m", "http.server", "8888", "--bind", "127.0.0.1"], root)
        print("FE started on :8888")

    print("http://localhost:8888")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
