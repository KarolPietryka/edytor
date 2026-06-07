# Edytor — PRD (MVP)

## Stack

| Serwis | Port | Pliki |
|--------|------|-------|
| FE | 8888 | `index.html`, `app.js` |
| BE | 3000 | `backend/server.py` |

## Uruchomienie

```powershell
python .cursor/skills/edytor/scripts/start_edytor.py .
```

Restart (kill + start):

```powershell
python .cursor/skills/reset/scripts/reset_edytor.py .
```

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
