# F00 INFOCYTE

2026-11-07 — silo cree. CODEBASE vide. Aucun parseur.

2026-11-07 — PHASE-02 PredictLix.
- `CODEBASE/predictlix.py` : parse HTML public (fixture locale) → `vanus.slate.v1`.
- `CODEBASE/run.py` : IN HTML fichier → OUT JSON. Pas de GET reseau dans cette phase.
- Unite = match (home/away/kickoff). Marches = champs (`odds.1x2`, `ev`, `pinnacle` si deja dans la page).
- UA clair : `VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)`.
- Ligues vues dans la fixture : La Liga (`/predictions/spain/la-liga/`).
- Pas DSP, pas MetaPred, pas runner multi-index.
