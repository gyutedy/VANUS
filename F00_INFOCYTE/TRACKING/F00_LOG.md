# F00 INFOCYTE

2026-11-07 — silo cree. CODEBASE vide. Aucun parseur.

2026-11-07 — PHASE-02 PredictLix.
- `CODEBASE/predictlix.py` : parse HTML public (fixture locale) → `vanus.slate.v1`.
- `CODEBASE/run.py` : IN HTML fichier → OUT JSON. Pas de GET reseau dans cette phase.
- Unite = match (home/away/kickoff). Marches = champs (`odds.1x2`, `ev`, `pinnacle` si deja dans la page).
- UA clair : `VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)`.
- Ligues vues dans la fixture : La Liga (`/predictions/spain/la-liga/`).
- Pas DSP, pas MetaPred, pas runner multi-index.

2026-11-07 — PHASE-03 DailySportPick.
- `CODEBASE/dailysportpick.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par competition.
- `run.py` : `--index dailysportpick` ecrit `slate_dailysportpick_<comp>_<date>.json`.
- Unite = match. Pick/cotes absents → `null` / `{}`. Extra cards inclus.
- Ligues vues dans la fixture : La Liga, Premier League, Serie A. Chemin whitelist : `https://dailysportpick.com/fr/`.
- Pas MetaPred, pas FootInsights, pas runner multi-index.

2026-11-07 — PHASE-04 MetaPred.
- `CODEBASE/metapred.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par competition.
- Today only : slug `DD-MM-YYYY` hors `slate_date` ignore. Blocs Demain/Hier ignores.
- Ligues vues dans la fixture : Premier League, La Liga. Chemin whitelist : `https://metapred.com/fr/pronostic/aujourd-hui`.
- Pas FootInsights, pas BeSoccer, pas runner multi-index.

2026-11-07 — PHASE-05 FootInsights.
- `CODEBASE/footinsights.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par competition.
- Tips collables (home/away/kickoff) → lignes match. Tip locked → pick/odds nuls, match conserve.
- Articles blog → `parse_blog_refs` slugs seulement. Pas de copie markdown (F02).
- Ligues vues dans la fixture : Premier League, La Liga. Chemin whitelist : `https://footinsights.com/predictions/`.
- Pas BeSoccer, pas runner multi-index.
