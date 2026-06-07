# Edytor — PRD (MVP)

## Stack

| Serwis | Port | Pliki |
|--------|------|-------|
| FE | 8888 | `index.html`, `app.js` |
| BE | 3000 | `backend/server.py` |

## Uruchomienie

**Dev (Cursor / repo):**

```powershell
python .cursor/skills/edytor/scripts/start_edytor.py .
```

**Windows — okna CMD (zalecane lokalnie):**

```powershell
Edytor.cmd
```

albo:

```powershell
python -m launcher.start .
```

Restart:

```powershell
EdytorReset.cmd
python -m launcher.reset . --debug
```

Otwierają się **dwa osobne okna CMD** (BE :3000, FE :8888). Zamknięcie okna = stop serwera.

## EXE (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File build/build_exe.ps1
```

W `dist/`: `Edytor.exe`, `EdytorBE.exe`, `EdytorFE.exe` — trzymaj w jednym folderze.

- `Edytor.exe` — launcher (BE + FE w osobnych oknach CMD)
- `EdytorBE.exe` / `EdytorFE.exe` — osobne okna CMD (zastrzel = zamknij okno)
- Klucz AI: `%LOCALAPPDATA%\Edytor\.env` (wzoruj na `.env.example`)
- Drafty: `backend/data/drafts/` obok exe

## Pętla AI (`POST /api/ai`)

Szablon: `backend/data/template_ai.md` — definiuje kształt `ai.md`.

### Flow (jeden komentarz = jeden krok)

1. Request na BE (`POST /api/ai`)
2. Serwer bierze **ostatni draft** z `backend/data/drafts/`
3. Bierze **kolejny komentarz** (`komentarz_001`, `komentarz_002`, …)
4. Łączy `{tekst}` + `{komentarze}` przez `template_ai.md` → zapisuje **`ai.md`** z placeholderem w `Final version:` (`Odpowiedz z AI. Obudz sie`)
5. Do modelu idzie prompt (treść szablonu + instrukcja formatu, **bez** wypełnionego `Final version`)
6. Odpowiedź AI trafia do sekcji `Final version:` w `ai.md`
7. **`DEBUG=false`** — tekst z `Final version` → `{tekst}` na następny krok; następny komentarz → `{komentarze}` → pkt 4
8. **`DEBUG=true`** — pełny `ai.md` po kroku → też `data/ai/ai_001.md`, `ai_002.md`, …; `ai.md` = ostatni stan

Po pętli: ostatni `final_text` → nowy plik draft.

### Przykład sekcji po odpowiedzi AI

```markdown
Final version:
"
Skrócony tekst po edycji przez AI...
"
```

## Parametr `DEBUG`

| `DEBUG` | Zapis `ai.md` | Historia |
|---------|---------------|----------|
| `false` (domyślnie) | Nadpisuje `backend/data/ai.md` | brak |
| `true` | Nadpisuje `ai.md` + snapshot `data/ai/ai_XXX.md` | tak |

### Jak włączyć

**`.env`:** `DEBUG=true`

**Flaga przy starcie:**

```powershell
python .cursor/skills/edytor/scripts/start_edytor.py . --debug
python .cursor/skills/reset/scripts/reset_edytor.py . --debug
```

**Sesja PowerShell:**

```powershell
$env:DEBUG="true"
.\.venv\Scripts\python.exe backend\server.py
```

## API (skrót)

- `POST /api/draft` — zapis draftu
- `POST /api/ai` — pętla AI po komentarzach; JSON: `debug`, `steps`, `final_text`

## Cleanup temp

```powershell
python .cursor/skills/usun_temp/scripts/usun_temp.py .
```

Usuwa drafty powyżej checkpointu oraz numerowane `data/ai/ai_XXX.md` (tryb debug).
