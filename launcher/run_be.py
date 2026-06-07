"""Backend Flask — osobne okno CMD (:3000)."""

import os
import sys
from pathlib import Path

from launcher.bootstrap import import_backend_module, resolve_root
from launcher.paths import apply_edytor_env, backend_dir


def set_console_title(title: str) -> None:
    if sys.platform == "win32":
        os.system(f"title {title}")


def main() -> int:
    root = resolve_root()
    apply_edytor_env(root)
    set_console_title("Edytor BE :3000")

    be = backend_dir()
    sys.path.insert(0, str(be))

    env_config = import_backend_module(root, "env_config")
    env_config.load_dotenv(root)

    server = import_backend_module(root, "server")

    print(f"BE root: {root}")
    print(f"Data:    {root / 'backend' / 'data'}")
    print(f"DEBUG:   {env_config.is_debug()} // ai snapshoty: data/ai/ai_XXX.md")
    print("Ctrl+C lub zamknij okno = stop serwera")
    server.app.run(host="127.0.0.1", port=3000, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
