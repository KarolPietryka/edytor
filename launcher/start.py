"""Uruchamia BE + FE w osobnych oknach CMD."""

import os
import socket
import subprocess
import sys
from pathlib import Path

from launcher.bootstrap import load_env_config, resolve_root
from launcher.paths import is_frozen, venv_python
from launcher.system_state import (
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


def spawn_server_console(root: Path, title: str, command: list[str]) -> None:
    if sys.platform == "win32":
        inner = subprocess.list2cmdline(command)
        # /c — okno CMD zamyka się gdy proces serwera umiera (reset / kill portu)
        subprocess.Popen(
            ["cmd", "/c", "start", title, "cmd", "/c", inner],
            cwd=str(root),
            env=os.environ.copy(),
        )
        return
    subprocess.Popen(command, cwd=str(root), start_new_session=True)


def be_command(root: Path, py: Path) -> list[str]:
    if is_frozen():
        return [str(root / "EdytorBE.exe")]
    return [str(py), "-m", "launcher.run_be"]


def fe_command(root: Path, py: Path) -> list[str]:
    if is_frozen():
        return [str(root / "EdytorFE.exe")]
    return [str(py), "-m", "launcher.run_fe"]


def start_stack(root: Path) -> tuple[int | None, int | None]:
    py = venv_python(root)
    be_pid = None
    fe_pid = None

    if port_open(BE_PORT):
        print(f"BE already on :{BE_PORT}")
        be_pid = resolve_port_pid(BE_PORT, wait_s=1.0)
    else:
        spawn_server_console(root, f"Edytor BE :{BE_PORT}", be_command(root, py))
        print(f"BE started on :{BE_PORT}")
        be_pid = resolve_port_pid(BE_PORT, wait_s=6.0)

    if port_open(FE_PORT):
        print(f"FE already on :{FE_PORT}")
        fe_pid = resolve_port_pid(FE_PORT, wait_s=1.0)
    else:
        spawn_server_console(root, f"Edytor FE :{FE_PORT}", fe_command(root, py))
        print(f"FE started on :{FE_PORT}")
        fe_pid = resolve_port_pid(FE_PORT, wait_s=6.0)

    if not be_pid or not fe_pid:
        be_cmd, fe_cmd = find_be_fe_pids_by_cmdline(root)
        if not be_pid:
            be_pid = be_cmd
        if not fe_pid:
            fe_pid = fe_cmd

    return be_pid, fe_pid


def main(argv: list[str] | None = None) -> int:
    raw = list(argv if argv is not None else sys.argv[1:])
    root = resolve_root(raw)
    env_config = load_env_config(root)

    env_config.load_dotenv(root)
    env_config.apply_debug_argv(raw)

    if not is_frozen() and not (root / "backend" / "server.py").exists():
        print(f"ERR: not edytor root: {root}", file=sys.stderr)
        return 1

    be_pid, fe_pid = start_stack(root)
    path = write_system_md(root, be_pid, fe_pid)
    print(f"System.md updated // BE pid={be_pid} FE pid={fe_pid}")
    print(f"System: {path}")
    if env_config.is_debug():
        print("DEBUG=true // ai.md + snapshoty data/ai/ai_XXX.md")
    else:
        print("DEBUG=false // tylko data/ai.md")
    print(f"http://localhost:{FE_PORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
