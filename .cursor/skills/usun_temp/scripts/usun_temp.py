#!/usr/bin/env python3
"""Usuwa tymczasowe drafty nowsze niż podany checkpoint (np. 02_2026_06_07)."""

import json
import re
import sys
from pathlib import Path

DRAFT_PATTERN = re.compile(r"^(\d{2})_(\d{4}_\d{2}_\d{2})\.md$")
LEGACY_AI_PATTERN = re.compile(r"^ai_\d{3}\.md$")
LEGACY_FINAL_PATTERN = re.compile(r"^final_v_\d{3}\.md$")
DEFAULT_KEEP = "02_2026_06_07"


def parse_keep(keep_stem: str) -> tuple[str, int]:
    match = DRAFT_PATTERN.match(f"{keep_stem}.md")
    if not match:
        raise ValueError(f"invalid keep draft: {keep_stem}")
    return match.group(2), int(match.group(1))


def collect_drafts_to_delete(drafts_dir: Path, keep_day: str, keep_ver: int) -> list[Path]:
    to_delete = []
    if not drafts_dir.exists():
        return to_delete

    for path in sorted(drafts_dir.glob("*.md")):
        match = DRAFT_PATTERN.match(path.name)
        if not match:
            continue
        ver = int(match.group(1))
        day = match.group(2)
        if (day, ver) > (keep_day, keep_ver):
            to_delete.append(path)
    return to_delete


def collect_legacy_to_delete(data_dir: Path) -> list[Path]:
    to_delete = []
    for sub, pattern in (
        (data_dir / "ai", LEGACY_AI_PATTERN),
        (data_dir / "final_v", LEGACY_FINAL_PATTERN),
    ):
        if not sub.exists():
            continue
        for path in sorted(sub.glob("*.md")):
            if pattern.match(path.name):
                to_delete.append(path)
    return to_delete


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    keep_stem = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_KEEP

    if not (root / "backend" / "server.py").exists():
        print(json.dumps({"ok": False, "error": f"not edytor root: {root}"}))
        return 1

    try:
        keep_day, keep_ver = parse_keep(keep_stem)
    except ValueError as err:
        print(json.dumps({"ok": False, "error": str(err)}))
        return 1

    data_dir = root / "backend" / "data"
    drafts_dir = data_dir / "drafts"

    deleted = []
    for path in collect_drafts_to_delete(drafts_dir, keep_day, keep_ver):
        path.unlink()
        deleted.append(str(path.relative_to(root)).replace("\\", "/"))

    for path in collect_legacy_to_delete(data_dir):
        path.unlink()
        deleted.append(str(path.relative_to(root)).replace("\\", "/"))

    result = {
        "ok": True,
        "keep": keep_stem,
        "deleted": deleted,
        "count": len(deleted),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
