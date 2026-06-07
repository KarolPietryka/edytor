"""Zapis i odczyt PIDów serwisów edytor w System.md (root workspace)."""

import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BE_PORT = 3000
FE_PORT = 8888

SERVER_MARKERS = (
    "server.py",
    "run_be.py",
    "launcher.run_be",
    "EdytorBE",
)
FE_MARKERS = (
    "http.server",
    "run_fe.py",
    "launcher.run_fe",
    "EdytorFE",
)


def system_md_path(root: Path) -> Path:
    return root.resolve() / "System.md"


def _port_in_line(line: str, port: int) -> bool:
    return re.search(rf":{port}(?:\s|$)", line) is not None


def find_pids_on_port(port: int) -> list[int]:
    pids = []
    if sys.platform != "win32":
        return pids

    try:
        ps = (
            f"(Get-NetTCPConnection -LocalPort {port} -State Listen "
            f"-ErrorAction SilentlyContinue).OwningProcess"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        for line in out.stdout.splitlines():
            line = line.strip()
            if not line.isdigit():
                continue
            pid = int(line)
            if pid not in pids:
                pids.append(pid)
        if pids:
            return pids
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return pids

    for line in out.stdout.splitlines():
        if "LISTENING" not in line or not _port_in_line(line, port):
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid not in pids:
            pids.append(pid)
    return pids


def _edytor_process_rows(root: Path) -> list[tuple[int, str]]:
    rows = []
    if sys.platform != "win32":
        return rows

    root_s = str(root.resolve()).replace("'", "''")
    ps = f"""
$root = '{root_s}'
Get-CimInstance Win32_Process |
  Where-Object {{
    $n = $_.Name
    ($n -eq 'python.exe' -or $n -eq 'pythonw.exe' -or $n -like 'Edytor*.exe') -and
    $_.CommandLine -and $_.CommandLine -like "*$root*"
  }} |
  ForEach-Object {{ "$($_.ProcessId)|$($_.CommandLine)" }}
"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return rows

    for line in out.stdout.splitlines():
        if "|" not in line:
            continue
        pid_s, cmd = line.split("|", 1)
        pid_s = pid_s.strip()
        if not pid_s.isdigit():
            continue
        rows.append((int(pid_s), cmd))
    return rows


def _cmd_matches(cmd: str, markers: tuple[str, ...], port: int | None = None) -> bool:
    if not any(marker in cmd for marker in markers):
        return False
    if port is None:
        return True
    return str(port) in cmd


def find_edytor_pids_by_cmdline(root: Path) -> list[int]:
    pids = []
    for pid, cmd in _edytor_process_rows(root):
        if _cmd_matches(cmd, SERVER_MARKERS, BE_PORT) or _cmd_matches(cmd, FE_MARKERS, FE_PORT):
            if pid not in pids:
                pids.append(pid)
    return pids


def find_be_fe_pids_by_cmdline(root: Path) -> tuple[int | None, int | None]:
    be_pid = None
    fe_pid = None
    for pid, cmd in _edytor_process_rows(root):
        if be_pid is None and _cmd_matches(cmd, SERVER_MARKERS):
            be_pid = pid
        if fe_pid is None and _cmd_matches(cmd, FE_MARKERS, FE_PORT):
            fe_pid = pid
    return be_pid, fe_pid


def kill_pid(pid: int) -> bool:
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return r.returncode == 0
        import os
        os.kill(pid, 9)
        return True
    except OSError:
        return False


def write_system_md(root: Path, be_pid: int | None, fe_pid: int | None) -> Path:
    path = system_md_path(root)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    be_val = str(be_pid) if be_pid else "-"
    fe_val = str(fe_pid) if fe_pid else "-"
    content = f"""# System — edytor dev stack

| serwis | port | pid |
|--------|------|-----|
| BE | {BE_PORT} | {be_val} |
| FE | {FE_PORT} | {fe_val} |

_updated: {now}_
"""
    path.write_text(content, encoding="utf-8")
    return path


def read_system_md(root: Path) -> dict:
    path = system_md_path(root)
    if not path.exists():
        return {"be_pid": None, "fe_pid": None}

    text = path.read_text(encoding="utf-8")
    be_match = re.search(r"\|\s*BE\s*\|\s*\d+\s*\|\s*(\d+|-)\s*\|", text)
    fe_match = re.search(r"\|\s*FE\s*\|\s*\d+\s*\|\s*(\d+|-)\s*\|", text)

    def parse_pid(match):
        if not match:
            return None
        val = match.group(1).strip()
        if val == "-":
            return None
        try:
            return int(val)
        except ValueError:
            return None

    return {
        "be_pid": parse_pid(be_match),
        "fe_pid": parse_pid(fe_match),
    }


def resolve_port_pid(port: int, wait_s: float = 0) -> int | None:
    deadline = time.time() + wait_s
    while True:
        pids = find_pids_on_port(port)
        if pids:
            return pids[0]
        if time.time() >= deadline:
            return None
        time.sleep(0.25)


def _parent_cmd_pid_for_port(port: int) -> int | None:
    ps = f"""
$p = (Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue |
  Select-Object -First 1).OwningProcess
if (-not $p) {{ return }}
$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$p"
while ($proc) {{
  if ($proc.Name -eq 'cmd.exe') {{ $proc.ProcessId; return }}
  if (-not $proc.ParentProcessId) {{ return }}
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
}}
"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    line = out.stdout.strip().splitlines()
    if not line:
        return None
    val = line[-1].strip()
    return int(val) if val.isdigit() else None


def kill_edytor_console_windows() -> list[int]:
    killed = []
    if sys.platform != "win32":
        return killed

    targets = []
    for port in (BE_PORT, FE_PORT):
        cmd_pid = _parent_cmd_pid_for_port(port)
        if cmd_pid:
            targets.append(cmd_pid)

    ps = """
Get-Process cmd -ErrorAction SilentlyContinue |
  Where-Object {
    $t = $_.MainWindowTitle
    $t -and ($t -like 'Edytor BE*' -or $t -like 'Edytor FE*')
  } |
  ForEach-Object { $_.Id }
"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        for line in out.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                targets.append(int(line))
    except (OSError, subprocess.TimeoutExpired):
        pass

    for pid in dict.fromkeys(targets):
        if kill_pid(pid):
            killed.append(pid)
    return killed


def kill_edytor_processes(root: Path) -> list[int]:
    killed = []

    for pid in kill_edytor_console_windows():
        if pid not in killed:
            killed.append(pid)

    state = read_system_md(root)
    targets = []
    for key in ("be_pid", "fe_pid"):
        if state.get(key):
            targets.append(state[key])
    for port in (BE_PORT, FE_PORT):
        targets.extend(find_pids_on_port(port))
    targets.extend(find_edytor_pids_by_cmdline(root))

    for pid in dict.fromkeys(targets):
        if kill_pid(pid) and pid not in killed:
            killed.append(pid)

    for pid in kill_edytor_console_windows():
        if pid not in killed:
            killed.append(pid)

    if killed:
        time.sleep(1)
    return killed
