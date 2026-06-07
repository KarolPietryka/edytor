"""Ścieżki i import modułów z backend/ bez konfliktów sys.path."""

import importlib.util
import sys
from pathlib import Path

from launcher.paths import app_root


def _clean_path_arg(value: str) -> str:
  # CMD: "%~dp0" + trailing \ → path ending with literal "
    return value.strip().strip('"').rstrip("\\/")


def resolve_root(argv: list[str] | None = None) -> Path:
    raw = list(argv if argv is not None else sys.argv[1:])
    root = app_root()
    if raw and not raw[0].startswith("-"):
        root = Path(_clean_path_arg(raw[0])).resolve()
    return root


def import_backend_module(root: Path, name: str):
    path = root / "backend" / f"{name}.py"
    if not path.is_file():
        raise ModuleNotFoundError(f"brak {path}")
    spec = importlib.util.spec_from_file_location(f"edytor_{name}", path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"nie mozna zaladowac {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_env_config(root: Path):
    return import_backend_module(root, "env_config")
