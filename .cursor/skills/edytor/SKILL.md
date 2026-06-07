---
name: edytor
description: >-
  Uruchamia projekt edytor (Flask BE :3000 + statyczny FE :8888). Używaj gdy
  user woła skill edytor, chce odpalić edytor, draft editor, purple haze
  console, lub pracę nad tym repo.
disable-model-invocation: true
---

# Edytor — dev stack

## OBOWIĄZKOWA pierwsza linia odpowiedzi

Za **każdym** wywołaniem tego skilla — **pierwsza linia** pierwszej wiadomości asystenta MUSI być dokładnie:

**http://localhost:8888**

Bez tekstu przed linkiem. Dopiero pod spodem reszta odpowiedzi.

## Projekt

Workspace root: `index.html`, `app.js`, `backend/server.py`, `.venv`.

| Serwis | Port | Rola |
|--------|------|------|
| FE (HTML) | **8888** | `index.html` + `app.js` |
| BE (Flask) | **3000** | `POST /api/draft` |

## Workflow przy każdym wywołaniu

1. Uruchom serwery skryptem (z roota workspace):

```powershell
python .cursor/skills/edytor/scripts/start_edytor.py .
```

Tryb debug AI (numerowane odpowiedzi w `data/ai/`):

```powershell
python .cursor/skills/edytor/scripts/start_edytor.py . --debug
```

Albo w `.env`: `DEBUG=true` (szczegóły w `PRD.md`).

2. Skrypt zapisuje PIDy do **`System.md`** w root (BE :3000, FE :8888).
3. Jeśli port zajęty — skrypt i tak raportuje i aktualizuje PID z portu; nie zabijaj procesów bez potrzeby (użyj skill **reset**).
4. Jeśli brak `.venv` — `python -m venv .venv` + `pip install -r backend/requirements.txt`.
5. Kontynuuj zadanie usera (edycja kodu, debug, itd.).

## Ręczny fallback

```powershell
.\.venv\Scripts\python.exe backend\server.py
.\.venv\Scripts\python.exe -m http.server 8888
```

Z debugiem:

```powershell
$env:DEBUG="true"; .\.venv\Scripts\python.exe backend\server.py
```

## Nie zmieniaj bez prośby

- FE URL w skillu: zawsze **8888**
- BE endpoint: `http://localhost:3000/api/draft`
