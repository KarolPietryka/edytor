import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def bundle_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_root()))
    return app_root()


def backend_dir() -> Path:
    bundled = bundle_root() / "backend"
    if bundled.is_dir():
        return bundled
    return app_root() / "backend"


def venv_python(root: Path) -> Path:
    win = root / ".venv" / "Scripts" / "python.exe"
    if win.exists():
        return win
    unix = root / ".venv" / "bin" / "python"
    if unix.exists():
        return unix
    return Path(sys.executable)


def user_env_path() -> Path | None:
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        return Path(local) / "Edytor" / ".env"
    return None


def ensure_runtime_dirs(root: Path) -> None:
    data = root / "backend" / "data"
    for sub in ("drafts", "ai", "final_v"):
        (data / sub).mkdir(parents=True, exist_ok=True)

    template = backend_dir() / "data" / "template_ai.md"
    target = data / "template_ai.md"
    if template.exists() and not target.exists():
        shutil.copy2(template, target)

    env_example = root / ".env.example"
    if not env_example.exists():
        env_example = bundle_root() / ".env.example"
    user_env = user_env_path()
    project_env = root / ".env"
    if (
        user_env
        and env_example.exists()
        and not user_env.exists()
        and not project_env.exists()
    ):
        user_env.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(env_example, user_env)


def apply_edytor_env(root: Path) -> None:
    data_dir = root / "backend" / "data"
    os.environ["EDYTOR_ROOT"] = str(root)
    os.environ["EDYTOR_DATA"] = str(data_dir)
    ensure_runtime_dirs(root)
