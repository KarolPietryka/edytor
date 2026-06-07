#!/usr/bin/env python3
"""Skanuje logi terminali Cursor i zwraca ostatni błąd z kontekstem."""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_AGE_SECONDS = 600

ERROR_PATTERNS = [
    re.compile(r'"([A-Z]+) /api/\S+ HTTP/1\.1" ([45]\d{2})'),
    re.compile(r'"([A-Z]+) \S+ HTTP/1\.1" ([45]\d{2})'),
    re.compile(r"\b(Traceback \(most recent call last\)):"),
    re.compile(r"\b(Error|Exception|ERR|FAILED|Fatal)\b", re.I),
    re.compile(r"\b(UnicodeEncodeError|OSError|HTTPError|ConnectionRefusedError)\b"),
    re.compile(r"\[ERR\]", re.I),
]

CONTEXT_LINES = 4
WERKZEUG_TS = re.compile(r"\[(\d{2}/\w{3}/\d{4} \d{2}:\d{2}:\d{2})\]")
TERMINAL_ENDED = re.compile(r"^ended_at:\s*(.+)$", re.M)
TERMINAL_STARTED = re.compile(r"^started_at:\s*(.+)$", re.M)


def parse_werkzeug_ts(line: str) -> float | None:
    match = WERKZEUG_TS.search(line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d/%b/%Y %H:%M:%S").timestamp()
    except ValueError:
        return None


def parse_iso_ts(value: str) -> float | None:
    try:
        raw = value.strip()
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def parse_terminal_times(text: str) -> dict:
    times = {}
    ended = TERMINAL_ENDED.search(text)
    started = TERMINAL_STARTED.search(text)
    if ended:
        ts = parse_iso_ts(ended.group(1))
        if ts is not None:
            times["ended_at"] = ts
    if started:
        ts = parse_iso_ts(started.group(1))
        if ts is not None:
            times["started_at"] = ts
    return times


def hit_occurred_at(hit: dict) -> float | None:
    ts = parse_werkzeug_ts(hit["text"])
    if ts is not None:
        return ts

    terminal = hit.get("terminal_times") or {}
    if terminal.get("ended_at") is not None:
        return terminal["ended_at"]
    if terminal.get("started_at") is not None:
        return terminal["started_at"]

    mtime = hit.get("mtime")
    if mtime is not None and mtime >= time.time() - hit.get("max_age_seconds", MAX_AGE_SECONDS):
        return mtime

    return None


def filter_fresh_hits(hits: list[dict], max_age_seconds: int = MAX_AGE_SECONDS) -> list[dict]:
    cutoff = time.time() - max_age_seconds
    fresh = []
    for hit in hits:
        hit["max_age_seconds"] = max_age_seconds
        occurred = hit_occurred_at(hit)
        if occurred is not None and occurred >= cutoff:
            hit["occurred_at"] = occurred
            fresh.append(hit)
    return fresh


def find_terminals_dir(workspace: Path) -> Path | None:
    projects = Path.home() / ".cursor" / "projects"
    if not projects.exists():
        return None

    workspace_slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(workspace.resolve())).strip("-").lower()
    candidates = sorted(projects.glob("*/terminals"), key=lambda p: p.stat().st_mtime, reverse=True)

    for terminals in candidates:
        if workspace_slug and workspace_slug in str(terminals).lower():
            return terminals

    return candidates[0] if candidates else None


def scan_file(path: Path) -> list[dict]:
    hits = []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        lines = raw.splitlines()
        mtime = path.stat().st_mtime
    except OSError:
        return hits

    terminal_times = parse_terminal_times(raw)

    for idx, line in enumerate(lines):
        for pattern in ERROR_PATTERNS:
            if pattern.search(line):
                start = max(0, idx - CONTEXT_LINES)
                end = min(len(lines), idx + CONTEXT_LINES + 1)
                hits.append({
                    "file": str(path),
                    "line": idx + 1,
                    "text": line.strip(),
                    "context": lines[start:end],
                    "mtime": mtime,
                    "terminal_times": terminal_times,
                })
                break

    return hits


def classify_error(text: str) -> str:
    lower = text.lower()
    if "404" in lower and "/api/" in lower:
        return "endpoint_404"
    if "connection refused" in lower or "winerror 10061" in lower:
        return "server_down"
    if "405" in lower:
        return "method_not_allowed"
    if "500" in lower:
        return "server_error"
    if "traceback" in lower:
        return "python_traceback"
    if "no draft files" in lower:
        return "no_drafts"
    return "unknown"


def suggest_fix(kind: str) -> list[str]:
    fixes = {
        "endpoint_404": [
            "Stary proces Flask na :3000 — brakuje nowego endpointu w kodzie.",
            "Zabij procesy na porcie 3000 i uruchom BE od nowa: .venv/Scripts/python.exe backend/server.py",
            "Sprawdz app.url_map — endpoint musi byc w dzialajacym procesie.",
        ],
        "server_down": [
            "BE nie dziala. Uruchom: python .cursor/skills/edytor/scripts/start_edytor.py .",
            "Albo recznie: .venv/Scripts/python.exe backend/server.py",
        ],
        "method_not_allowed": [
            "Zly HTTP method — sprawdz czy FE wysyla POST tam gdzie BE oczekuje POST.",
        ],
        "server_error": [
            "Blad 500 na BE — przeczytaj traceback w logach i napraw server.py.",
        ],
        "python_traceback": [
            "Wyjatek Pythona — napraw linie ze stack trace w backend/server.py.",
        ],
        "no_drafts": [
            "Brak plikow w backend/data/drafts — najpierw Transmit lub komentarz z tekstem.",
        ],
        "unknown": [
            "Przeczytaj kontekst bledu w logu i powiaz z ostatnia akcja usera (Transmit/AI/comment).",
        ],
    }
    return fixes.get(kind, fixes["unknown"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Znajdz ostatni blad w logach")
    parser.add_argument("workspace", nargs="?", default=".", help="Root workspace")
    parser.add_argument("--terminals-dir", help="Sciezka do folderu terminals Cursor")
    parser.add_argument(
        "--max-age",
        type=int,
        default=MAX_AGE_SECONDS,
        help="Ignoruj bledy starsze niz N sekund (domyslnie 600 = 10 min)",
    )
    args = parser.parse_args()
    max_age = max(1, args.max_age)

    workspace = Path(args.workspace).resolve()
    terminals = Path(args.terminals_dir) if args.terminals_dir else find_terminals_dir(workspace)

    if not terminals or not terminals.exists():
        print(json.dumps({
            "ok": False,
            "error": "terminals_dir_not_found",
            "hint": "Uruchom BE recznie w terminalu Cursor albo podaj --terminals-dir",
        }, ensure_ascii=False, indent=2))
        return 1

    all_hits = []
    for path in terminals.glob("*.txt"):
        all_hits.extend(scan_file(path))

    fresh_hits = filter_fresh_hits(all_hits, max_age)

    if not fresh_hits:
        print(json.dumps({
            "ok": True,
            "found": False,
            "terminals_dir": str(terminals),
            "max_age_seconds": max_age,
            "scanned_errors": len(all_hits),
            "message": (
                f"Brak bledow z ostatnich {max_age // 60} min. "
                "Starsze logi sa ignorowane. Uruchom BE recznie, powtorz akcje i sprobuj ponownie."
            ),
        }, ensure_ascii=False, indent=2))
        return 0

    last = max(fresh_hits, key=lambda h: (h["occurred_at"], h["line"]))
    kind = classify_error(last["text"])
    result = {
        "ok": True,
        "found": True,
        "terminals_dir": str(terminals),
        "max_age_seconds": max_age,
        "scanned_errors": len(all_hits),
        "source_file": last["file"],
        "line": last["line"],
        "error": last["text"],
        "context": last["context"],
        "kind": kind,
        "suggested_fixes": suggest_fix(kind),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
