---
name: log_fix
description: >-
  Skanuje logi serwera (terminale Cursor), znajduje ostatni błąd i próbuje
  go naprawić. Używaj gdy user woła log_fix, coś nie działa, błąd requestu,
  404/500 na API, lub prosi o sprawdzenie logów i fix.
disable-model-invocation: true
---

# log_fix — ostatni błąd z logów → fix

## Workflow (OBOWIĄZKOWY)

1. **Znajdź ostatni błąd** — uruchom skrypt z roota workspace:

```powershell
python .cursor/skills/log_fix/scripts/find_last_error.py .
```

2. **Przeczytaj JSON** — pola: `error`, `context`, `kind`, `suggested_fixes`, `max_age_seconds`.

3. **Tylko świeże logi** — skrypt bierze błędy z **ostatnich 10 minut** (domyślnie 600 s). Starsze są **ignorowane**. `found: false` + `scanned_errors` > 0 = same stare logi, nie fixuj na ich podstawie.

4. **Potwierdź diagnozę** — jeśli trzeba, otwórz `source_file` i przeczytaj kontekst wokół `line`.

5. **Napraw** — według `kind` (tabela niżej) + minimalna zmiana w kodzie jeśli to bug, nie tylko restart.

6. **Zweryfikuj** — po fixie:
   - uruchom / zrestartuj BE jeśli trzeba
   - wyślij test request do zepsutego endpointu
   - uruchom `find_last_error.py` ponownie lub sprawdź brak nowego błędu

7. **Raport dla usera** — krótko: co było w logu, co zrobiłeś, czy działa.

## Gdzie są logi (edytor)

| Źródło | Kiedy widać logi |
|--------|------------------|
| Terminale Cursor (`~/.cursor/projects/*/terminals/*.txt`) | Gdy BE odpalony **ręcznie** w terminalu |
| `start_edytor.py` | Logi **wyciszone** (`DEVNULL`) — mało użyteczne |
| Status w FE (`#status`) | Tylko błąd z perspektywy przeglądarki |

Jeśli `found: false` — najpierw sprawdź `max_age_seconds`: może nie ma błędów z ostatnich 10 min (stare logi odfiltrowane). Poproś usera o ręczny start BE **albo** sam odpal:

```powershell
.\.venv\Scripts\python.exe backend\server.py
```

i powtórz reprodukcję błędu, potem `find_last_error.py`.

## Playbook: kind → fix

| kind | Typowy problem | Fix |
|------|----------------|-----|
| `endpoint_404` | Stary Flask na :3000, brak nowego route (np. `/api/ai`) | Zabij procesy na :3000, uruchom `backend/server.py` z aktualnym kodem |
| `server_down` | BE nie działa | `python .cursor/skills/edytor/scripts/start_edytor.py .` lub ręczny start |
| `method_not_allowed` | FE wysyła zły HTTP method | Sprawdź `app.js` vs dekorator `@app.post` w `server.py` |
| `server_error` | Wyjątek w `server.py` | Traceback w kontekście → napraw kod, test `app.test_client()` |
| `python_traceback` | Crash Pythona | Jak wyżej |
| `no_drafts` | Brak plików w `backend/data/drafts` | Transmit lub komentarz z `text` |
| `unknown` | Inne | Kontekst logu + ostatnia akcja usera |

### Stary proces na :3000 (częste)

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen | Select-Object OwningProcess -Unique
Stop-Process -Id <PID> -Force
.\.venv\Scripts\python.exe backend\server.py
```

Potem test:

```powershell
.\.venv\Scripts\python.exe -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/api/ai', data=b'{}', method='POST')"
```

(dostosuj URL do endpointu z błędu)

## Zasady naprawy

- **MVP** — najmniejszy fix który przywraca działanie.
- **Nie zgaduj** — fix wynika z logu + kodu.
- **Reuse** — nie duplikuj logiki BE; popraw istniejące funkcje.
- **Nie commituj** bez prośby usera.
- Po restarcie BE z `debug=True` — nowy kod ładuje się automatycznie **tylko w jednym procesie**; duplikaty na porcie = stary kod.

## Format odpowiedzi

```markdown
## Ostatni błąd
<1 linia z logu>

## Przyczyna
<krótko>

## Fix
<co zrobiłem>

## Weryfikacja
<test / wynik>
```
