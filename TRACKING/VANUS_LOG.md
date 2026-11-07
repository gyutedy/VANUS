# VANUS_LOG

## 2026-11-07

- Temple ouvert : structure + docs + contrats.
- Aucun code metier.
- Runtime cible : PythonAnywhere.
- Depot public : https://github.com/gyutedy/VANUS
- Pas lie a Perturabo.
- Plan 14 phases : `docs/05_IMPLEMENTATION.md` (une phase = une session).
- PHASE-01 : `VANUS_CUSTOS.py`, pytest, fixtures JSON, 21 tests. Zero parseur.
- PHASE-02 : F00 PredictLix. `predictlix.py` + `run.py`, fixtures HTML, 28 tests. Un site. Pas DSP.
- PHASE-03 : F00 DailySportPick. `dailysportpick.py`, fixtures HTML, 34 tests. OUT separe par index. Pas MetaPred.
- PHASE-04 : F00 MetaPred. `metapred.py`, fixtures HTML, 40 tests. Today only, par competition. Pas FootInsights.
- PHASE-05 : F00 FootInsights. `footinsights.py`, fixtures HTML, 47 tests. Tips → lignes match si collables ; article → `raw_ref` seulement. Pas BeSoccer.
- Prochaine session : PHASE-06 BeSoccer + runner.
