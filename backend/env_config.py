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


def load_dotenv(workspace_root: Path) -> Path | None:
    candidates = [
        workspace_root / ".env",
        workspace_root / "backend" / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
        return path
    return None
