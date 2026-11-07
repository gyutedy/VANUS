# TARIEL

2026-11-07 — PHASE-13 orchestrateur.
- `CODEBASE/tariel.py` : poll `poll_minutes` (defaut 120, plancher 30). subprocess F00→F01→F02→F03→F05 (lecture) puis F04 (alerte). Jusqu'au KO.
- `CODEBASE/gates.py` : portes lecture / alerte. Ne parse pas.
- `CODEBASE/run.py` : `--once` une passe ; sinon boucle.
- Pas HTML. Pas d'import F00–F05.
