#!/usr/bin/env python3
"""Skanuje logi terminali Cursor i zwraca ostatnie błędy z interpretacją po polsku."""

import argparse
import json
import sys
from pathlib import Path

_LOG_FIX_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "log_fix" / "scripts"
sys.path.insert(0, str(_LOG_FIX_SCRIPTS))

import find_last_error as scanner  # noqa: E402

MAX_ERRORS = 3

INTERPRETATIONS = {
    "endpoint_404": {
        "interpretation_pl": (
            "Backend na porcie 3000 odpowiedział 404 — serwer działa, ale nie zna tego endpointu API."
        ),
        "hint_for_user": (
            "Żądanie dotarło do Flask, ale route nie istnieje w działającym procesie "
            "(np. stary serwer bez nowego endpointu albo zła ścieżka w FE)."
        ),
    },
    "server_down": {
        "interpretation_pl": (
            "Frontend nie mógł połączyć się z backendem — nic nie nasłuchuje na porcie 3000 "
            "albo połączenie zostało odrzucone."
        ),
        "hint_for_user": (
            "BE prawdopodobnie nie jest uruchomiony. Status w przeglądarce (#status) "
            "pokaże podobny komunikat (Failed to fetch / connection refused)."
        ),
    },
    "method_not_allowed": {
        "interpretation_pl": (
            "Backend zna ten URL, ale odrzucił metodę HTTP (np. POST zamiast GET lub odwrotnie)."
        ),
        "hint_for_user": (
            "FE wysyła inny typ żądania niż dekorator w server.py (@app.get vs @app.post)."
        ),
    },
    "server_error": {
        "interpretation_pl": (
            "Backend zwrócił 500 — podczas obsługi requestu wystąpił wyjątek w Pythonie."
        ),
        "hint_for_user": (
            "W kontekście logu szukaj tracebacku tuż przed lub po tej linii — tam jest przyczyna techniczna."
        ),
    },
    "python_traceback": {
        "interpretation_pl": (
            "Proces Pythona rzucił nieobsłużony wyjątek — serwer mógł przerwać obsługę requestu."
        ),
        "hint_for_user": (
            "Stack trace w kontekście wskazuje plik i linię kodu, gdzie coś poszło nie tak."
        ),
    },
    "no_drafts": {
        "interpretation_pl": (
            "Backend nie znalazł żadnych plików draft — katalog backend/data/drafts jest pusty."
        ),
        "hint_for_user": (
            "Edytor nie ma jeszcze tekstu do wczytania. Najpierw trzeba wysłać treść (Transmit lub komentarz)."
        ),
    },
    "missing_api_key": {
        "interpretation_pl": (
            "Funkcja AI wymaga klucza API, którego backend nie widzi w środowisku."
        ),
        "hint_for_user": (
            "Brakuje OPENAI_API_KEY lub CURSOR_API_KEY w pliku .env w root projektu. "
            "BE musi być zrestartowany po dodaniu klucza."
        ),
    },
    "failed_to_fetch": {
        "interpretation_pl": (
            "Przeglądarka nie dostała odpowiedzi od backendu — sieć, timeout, wyłączony serwer lub CORS."
        ),
        "hint_for_user": (
            "To perspektywa FE, nie log serwera. BE może być wyłączony, wisieć na starym kodzie "
            "albo nie odpowiadać na czas."
        ),
    },
    "template_error": {
        "interpretation_pl": (
            "Backend nie mógł wczytać szablonu AI (backend/data/template_ai.md)."
        ),
        "hint_for_user": (
            "Plik szablonu brakuje lub jest uszkodzony — funkcja AI nie wystartuje poprawnie."
        ),
    },
    "validation_error": {
        "interpretation_pl": (
            "Backend odrzucił request — brak wymaganych pól lub pusty tekst (błąd 400)."
        ),
        "hint_for_user": (
            "FE wysłało niepełne dane. To nie crash serwera, tylko walidacja wejścia."
        ),
    },
    "unknown": {
        "interpretation_pl": (
            "W logu jest komunikat błędu, który nie pasuje do typowych scenariuszy edytora."
        ),
        "hint_for_user": (
            "Przeczytaj kontekst wokół błędu i powiąż z ostatnią akcją (Transmit, AI, komentarz, draft)."
        ),
    },
}


def classify_error(text: str) -> str:
    lower = text.lower()
    if "openai_api_key" in lower or "cursor_api_key" in lower:
        return "missing_api_key"
    if "missing" in lower and "api_key" in lower:
        return "missing_api_key"
    if "brak klucza ai" in lower:
        return "missing_api_key"
    if "failed to fetch" in lower:
        return "failed_to_fetch"
    if "template not found" in lower or "template_ai" in lower:
        return "template_error"
    if '" 400 ' in lower or "empty text" in lower or "missing fields" in lower or "missing text" in lower:
        return "validation_error"
    return scanner.classify_error(text)


def interpret(kind: str) -> dict:
    return INTERPRETATIONS.get(kind, INTERPRETATIONS["unknown"])


def collect_errors(terminals: Path, max_errors: int, max_age_seconds: int) -> tuple[list[dict], int]:
    all_hits = []
    for path in terminals.glob("*.txt"):
        all_hits.extend(scanner.scan_file(path))

    scanned = len(all_hits)
    all_hits = scanner.filter_fresh_hits(all_hits, max_age_seconds)
    if not all_hits:
        return [], scanned

    all_hits.sort(key=lambda h: (h["occurred_at"], h["line"]))
    seen_text = set()
    unique = []
    for hit in reversed(all_hits):
        key = hit["text"]
        if key in seen_text:
            continue
        seen_text.add(key)
        unique.append(hit)
        if len(unique) >= max_errors:
            break

    unique.reverse()
    return unique, scanned


def build_entry(hit: dict) -> dict:
    kind = classify_error(hit["text"])
    meta = interpret(kind)
    return {
        "error": hit["text"],
        "kind": kind,
        "interpretation_pl": meta["interpretation_pl"],
        "context": hit["context"],
        "hint_for_user": meta["hint_for_user"],
        "source_file": hit["file"],
        "line": hit["line"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Interpretuj ostatnie bledy w logach edytor")
    parser.add_argument("workspace", nargs="?", default=".", help="Root workspace")
    parser.add_argument("--terminals-dir", help="Sciezka do folderu terminals Cursor")
    parser.add_argument("--max", type=int, default=MAX_ERRORS, help="Ile ostatnich bledow (domyslnie 3)")
    parser.add_argument(
        "--max-age",
        type=int,
        default=scanner.MAX_AGE_SECONDS,
        help="Ignoruj bledy starsze niz N sekund (domyslnie 600 = 10 min)",
    )
    args = parser.parse_args()
    max_errors = max(1, args.max)
    max_age = max(1, args.max_age)

    workspace = Path(args.workspace).resolve()
    terminals = Path(args.terminals_dir) if args.terminals_dir else scanner.find_terminals_dir(workspace)

    if not terminals or not terminals.exists():
        print(json.dumps({
            "ok": False,
            "error": "terminals_dir_not_found",
            "hint_for_user": (
                "Nie znaleziono logów terminali Cursor. Uruchom BE ręcznie w terminalu "
                "albo podaj --terminals-dir. start_edytor.py wycisza logi (DEVNULL)."
            ),
        }, ensure_ascii=False, indent=2))
        return 1

    hits, scanned = collect_errors(terminals, max_errors, max_age)
    if not hits:
        print(json.dumps({
            "ok": True,
            "found": False,
            "terminals_dir": str(terminals),
            "max_age_seconds": max_age,
            "scanned_errors": scanned,
            "message": (
                f"Brak błędów z ostatnich {max_age // 60} min — starsze logi są ignorowane. "
                "Jeśli coś nie działa, uruchom BE ręcznie w terminalu Cursor i powtórz akcję."
            ),
            "hint_for_user": (
                "Logi z start_edytor.py są wyciszone. Sprawdź też status w FE (#status) "
                "i PIDy w System.md — czy BE :3000 faktycznie działa."
            ),
        }, ensure_ascii=False, indent=2))
        return 0

    errors = [build_entry(h) for h in hits]
    print(json.dumps({
        "ok": True,
        "found": True,
        "terminals_dir": str(terminals),
        "max_age_seconds": max_age,
        "count": len(errors),
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
