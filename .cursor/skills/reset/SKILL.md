---
name: reset
description: >-
  Restartuje stack edytor: czyta PIDy z System.md, zabija procesy BE/FE,
  uruchamia od nowa jak skill edytor. Używaj gdy user woła reset, restart
  serwera, stary Flask, 404 na nowym endpoincie, lub chce świeży BE+FE.
disable-model-invocation: true
---

# Reset — kill + start edytor

## OBOWIĄZKOWA pierwsza linia odpowiedzi

**http://localhost:8888**

## Workflow

1. Uruchom z roota workspace:

```powershell
python .cursor/skills/reset/scripts/reset_edytor.py .
```

Z debugiem AI (przekazuje `--debug` do startu):

```powershell
python .cursor/skills/reset/scripts/reset_edytor.py . --debug
```

2. Skrypt:
   - czyta `System.md` (PIDy BE :3000, FE :8888)
   - zabija zapisane PIDy + procesy na portach 3000/8888
   - odpala `start_edytor.py` (ten sam co skill **edytor**)
   - aktualizuje `System.md` z nowymi PIDami

3. Potwierdź userowi nowe PIDy z outputu oraz linię `DEBUG=true/false`.

## Kiedy używać

- Stary kod na :3000 (np. 404 na `/api/ai`)
- Duplikaty procesów `server.py`
- Po większych zmianach w `backend/server.py` gdy auto-reload nie zadziałał

## Plik stanu

`System.md` w root workspace — generowany przez `start_edytor.py`, nie edytuj ręcznie.

## Nie zmieniaj bez prośby

- Porty: BE **3000**, FE **8888**
- Start zawsze przez `edytor/scripts/start_edytor.py` (reuse)
