import os
from pathlib import Path

DEBUG_TRUTHY = frozenset({"1", "true", "yes", "on"})


def is_debug() -> bool:
    return os.environ.get("DEBUG", "").strip().lower() in DEBUG_TRUTHY


def apply_debug_argv(argv: list[str]) -> list[str]:
    if "--debug" in argv:
        os.environ["DEBUG"] = "true"
        argv = [arg for arg in argv if arg != "--debug"]
    return argv


def _apply_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ[key] = val


def load_dotenv(workspace_root: Path) -> Path | None:
    # --debug z launchera (reset --debug) nie może zostać nadpisane przez .env
    pinned_debug = os.environ.get("DEBUG")

    candidates = []
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        candidates.append(Path(local) / "Edytor" / ".env")
    candidates.extend([
        workspace_root / ".env",
        workspace_root / "backend" / ".env",
    ])

    primary = None
    for path in candidates:
        if not path.exists():
            continue
        _apply_env_file(path)
        if path in (workspace_root / ".env", workspace_root / "backend" / ".env"):
            primary = path
        elif primary is None:
            primary = path

    if pinned_debug:
        os.environ["DEBUG"] = pinned_debug
    return primary
