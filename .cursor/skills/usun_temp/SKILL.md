---
name: usun_temp
description: >-
  Usuwa tymczasowe drafty nowsze niż checkpoint (domyślnie 02_2026_06_07)
  oraz numerowane pliki w data/ai (DEBUG). Używaj gdy user woła
  usun_temp, /usun_temp, chce wyczyścić śmieci po iteracji AI/draftów.
disable-model-invocation: true
---

# usun_temp — cleanup draftów i legacy temp

## Workflow

1. Uruchom z roota workspace:

```powershell
python .cursor/skills/usun_temp/scripts/usun_temp.py .
```

2. Opcjonalnie inny checkpoint (zostaw wszystko do tego pliku włącznie):

```powershell
python .cursor/skills/usun_temp/scripts/usun_temp.py . 02_2026_06_07
```

3. Przeczytaj JSON z outputu — pola: `deleted`, `count`, `keep`.

4. **Raport dla usera** — krótko: co usunięto, co zostało.

## Co usuwa

| Cel | Reguła |
|-----|--------|
| Drafty | `backend/data/drafts/NN_YYYY_MM_DD.md` gdzie `(data, NN) > (checkpoint)` |
| Debug AI | `backend/data/ai/ai_XXX.md` (gdy `DEBUG=true`) |
| Legacy final | `backend/data/final_v/final_v_XXX.md` (stary format) |

## Czego NIE usuwa

- `backend/data/ai.md` (bieżąca odpowiedź AI)
- `backend/data/template_ai.md`
- Drafty `<=` checkpoint (np. `00`, `01`, `02` dla `02_2026_06_07`)

## Nie zmieniaj bez prośby

- Domyślny checkpoint: **02_2026_06_07**
- Nie commituj bez prośby usera
