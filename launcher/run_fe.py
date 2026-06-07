"""Static FE — osobne okno CMD (:8888)."""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

from launcher.bootstrap import resolve_root
from launcher.paths import apply_edytor_env
from launcher.system_state import FE_PORT


def set_console_title(title: str) -> None:
    if sys.platform == "win32":
        os.system(f"title {title}")


def main() -> int:
    root = resolve_root()
    apply_edytor_env(root)
    os.chdir(root)
    set_console_title(f"Edytor FE :{FE_PORT}")

    print(f"FE root: {root}")
    print(f"URL:     http://127.0.0.1:{FE_PORT}")
    print("Ctrl+C lub zamknij okno = stop serwera")

    HTTPServer(("127.0.0.1", FE_PORT), SimpleHTTPRequestHandler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
