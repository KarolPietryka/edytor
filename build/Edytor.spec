# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

root = Path(os.path.dirname(os.path.abspath(SPEC)))

datas = [
    (str(root / "backend"), "backend"),
    (str(root / "index.html"), "."),
    (str(root / "app.js"), "."),
    (str(root / ".env.example"), "."),
]

hidden = [
    "flask",
    "flask_cors",
    "werkzeug",
    "jinja2",
    "click",
    "itsdangerous",
    "markupsafe",
]

a_be = Analysis(
    [str(root / "launcher" / "run_be.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    noarchive=False,
)
pyz_be = PYZ(a_be.pure)
exe_be = EXE(
    pyz_be,
    a_be.scripts,
    a_be.binaries,
    a_be.datas,
    [],
    name="EdytorBE",
    debug=False,
    console=True,
)

a_fe = Analysis(
    [str(root / "launcher" / "run_fe.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "index.html"), "."), (str(root / "app.js"), ".")],
    hiddenimports=[],
    noarchive=False,
)
pyz_fe = PYZ(a_fe.pure)
exe_fe = EXE(
    pyz_fe,
    a_fe.scripts,
    a_fe.binaries,
    a_fe.datas,
    [],
    name="EdytorFE",
    debug=False,
    console=True,
)

a_start = Analysis(
    [str(root / "launcher" / "start.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=["launcher.paths", "launcher.system_state"],
    noarchive=False,
)
pyz_start = PYZ(a_start.pure)
exe_start = EXE(
    pyz_start,
    a_start.scripts,
    a_start.binaries,
    a_start.datas,
    [],
    name="Edytor",
    debug=False,
    console=True,
)
