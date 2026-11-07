# F03 SPECULUM

2026-11-07 — silo cree. CODEBASE vide. Evolution + consensus a venir.

2026-11-07 — PHASE-10 evolution + alertes.
- `CODEBASE/speculum.py` : snapshot → `vanus.evolution.v1` (une vue, N lignes, marche 1x2/home). Pinnacle = `pinnacle_ref` seulement si deja dans les odds.
- `CODEBASE/run.py` : IN snapshots → OUT evolution + alert si consensus. Fingerprints dans `alert_seen.json`.
- 2 sources meme sens = `alarm`. Toutes les trouvees = `jackpot`. Absent ≠ vote. Meme fingerprint = pas de 2e alerte. 2→tous = nouvelle alerte.
- Pas CELL. Pas CIPHER. Pas Telegram.
