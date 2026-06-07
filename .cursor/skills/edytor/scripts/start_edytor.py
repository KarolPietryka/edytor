#!/usr/bin/env python3
"""Start edytor BE (:3000) and static FE (:8888). Idempotent-ish."""

import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))

from env_config import apply_debug_argv, is_debug, load_dotenv  # noqa: E402
from system_state import (
    BE_PORT,
    FE_PORT,
    find_be_fe_pids_by_cmdline,
    resolve_port_pid,
    write_system_md,
)


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
    kwargs = {"cwd": cwd}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen(cmd, **kwargs)


def main() -> int:
    argv = apply_debug_argv(list(sys.argv[1:]))
    root = Path(argv[0] if argv else ".").resolve()
    load_dotenv(root)
    py = venv_python(root)

    if not (root / "backend" / "server.py").exists():
        print(f"ERR: not edytor root: {root}", file=sys.stderr)
        return 1

    if port_open(BE_PORT):
        print("BE already on :3000")
        be_pid = resolve_port_pid(BE_PORT, wait_s=1.0)
    else:
        start([str(py), str(root / "backend" / "server.py")], root)
        print("BE started on :3000")
        be_pid = resolve_port_pid(BE_PORT, wait_s=4.0)

    if port_open(FE_PORT):
        print("FE already on :8888")
        fe_pid = resolve_port_pid(FE_PORT, wait_s=1.0)
    else:
        start([str(py), "-m", "http.server", str(FE_PORT), "--bind", "127.0.0.1"], root)
        print("FE started on :8888")
        fe_pid = resolve_port_pid(FE_PORT, wait_s=4.0)

    if not be_pid or not fe_pid:
        be_cmd, fe_cmd = find_be_fe_pids_by_cmdline(root)
        if not be_pid:
            be_pid = be_cmd
        if not fe_pid:
            fe_pid = fe_cmd

    path = write_system_md(root, be_pid, fe_pid)
    print(f"System.md updated // BE pid={be_pid} FE pid={fe_pid}")
    print(f"System: {path}")
    if is_debug():
        print("DEBUG=true // ai.md + snapshoty data/ai/ai_XXX.md")
    else:
        print("DEBUG=false // tylko data/ai.md")
    print("http://localhost:8888")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
