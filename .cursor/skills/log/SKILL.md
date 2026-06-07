---
name: log
description: >-
  Czyta i interpretuje logi serwera edytor — wyjaśnia po polsku co poszło nie
  tak, bez naprawy. Używaj gdy user woła /log, chce interpretację logów, pyta
  co było nie tak, co znaczy błąd w terminalu, lub chce zrozumieć 404/500/AI
  error bez automatycznego fixu.
disable-model-invocation: true
---

# log — interpretacja logów (bez naprawy)

**Nie naprawiaj** kodu ani serwera, chyba że user wyraźnie poprosi. To skill tylko do czytania i tłumaczenia logów. Do diagnozy + fixu użyj **log_fix**.

## Workflow (OBOWIĄZKOWY)

1. **Uruchom skrypt** z roota workspace:

```powershell
python .cursor/skills/log/scripts/interpret_logs.py .
```

2. **Przeczytaj JSON** — pola w `errors[]`: `error`, `kind`, `interpretation_pl`, `context`, `hint_for_user`.

3. **Tylko świeże logi** — skrypt bierze błędy z **ostatnich 10 minut** (`max_age_seconds: 600`). Starsze są **ignorowane**. Jeśli `found: false` i `scanned_errors` > 0 — były stare wpisy, nie aktualny problem.

4. **Opcjonalnie** — jeśli kontekst niejasny, otwórz `source_file` wokół `line` (tylko do lepszego wyjaśnienia, nie do fixu).

5. **Wyjaśnij userowi po polsku** — prostym językiem, bez komend naprawczych.

## Gdzie są logi (edytor)

| Źródło | Kiedy widać logi |
|--------|------------------|
| Terminale Cursor (`~/.cursor/projects/*/terminals/*.txt`) | Gdy BE odpalony **ręcznie** w terminalu |
| `start_edytor.py` | Logi **wyciszone** (`DEVNULL`) — mało użyteczne |
| `System.md` (root) | PIDy BE :3000 i FE :8888 — czy serwisy w ogóle działają |
| Status w FE (`#status`) | Błąd z perspektywy przeglądarki (np. Failed to fetch) |

Jeśli `found: false` — powiedz userowi: (a) brak **świeżych** błędów w ostatnich 10 min, (b) logi mogą być niewidoczne (wyciszone przez start_edytor) — niech odpali BE ręcznie, powtórzy błąd i woła /log ponownie. **Nie** restartuj serwera sam z siebie.

## kind → znaczenie (skrót)

| kind | Co to znaczy |
|------|----------------|
| `endpoint_404` | BE działa, ale nie ma tego route API |
| `server_down` | BE nie odpowiada na :3000 |
| `method_not_allowed` | Zła metoda HTTP (GET vs POST) |
| `server_error` / `python_traceback` | Wyjątek w backendzie |
| `no_drafts` | Brak plików w `backend/data/drafts` |
| `missing_api_key` | Brak OPENAI/CURSOR API key w `.env` |
| `failed_to_fetch` | FE nie dogadał się z BE (crash, timeout, CORS) |
| `validation_error` | Złe dane w requeście (400) |
| `unknown` | Inne — patrz kontekst |

## Format odpowiedzi

```markdown
## Co się stało
<1–2 zdania, ostatni błąd z logu>

## Dlaczego
<interpretation_pl ze skryptu + kontekst jeśli potrzebny>

## Co to znaczy dla Ciebie
<hint_for_user — bez komend fix, bez edycji kodu>

## Kontekst (opcjonalnie)
<starsze błędy z errors[] jeśli pomagają zrozumieć sytuację>
```

Jeśli user chce naprawę — zaproponuj skill **log_fix** lub zapytaj wprost.
