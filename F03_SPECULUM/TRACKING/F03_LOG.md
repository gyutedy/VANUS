# F03 SPECULUM

2026-11-07 — silo cree. CODEBASE vide. Evolution + consensus a venir.

2026-11-07 — PHASE-10 evolution + alertes.
- `CODEBASE/speculum.py` : snapshot → `vanus.evolution.v1` (une vue, N lignes, marche 1x2/home). Pinnacle = `pinnacle_ref` seulement si deja dans les odds.
- `CODEBASE/run.py` : IN snapshots → OUT evolution + alert si consensus. Fingerprints dans `alert_seen.json`.
- 2 sources meme sens = `alarm`. Toutes les trouvees = `jackpot`. Absent ≠ vote. Meme fingerprint = pas de 2e alerte. 2→tous = nouvelle alerte.
- Pas CELL. Pas CIPHER. Pas Telegram.

2026-11-10 — PHASE-15 contrat `vanus.signal.v1`.
- `CONTRACTS/schema_signal.json` colle du cahier B.2. Golden `tests/fixtures/json/signal.json`.
- Pas de `signals_export.py`. Pas de branchement `run.py` / TARIEL.

2026-11-10 — PHASE-16 `signals_export.py`.
- Collage cahier B.2. CLI autonome `--in` snapshots `--out` SHARED/OUT/signals.
- `tests/test_signal.py` : muet=null, isole/alarme, Pinnacle si deja la, ouvert/cloture, ecriture atomique.
- `run.py` et TARIEL non touches.

2026-11-10 — PHASE-17 branchement `--signal-out`.
- `run.py` : apres evolution/alert, `signals_export.aggregate` → `SHARED/OUT/signals`.
- TARIEL : meme etape F03, flag `--signal-out`. Pas d'etape separee. Pas dans ALERTE_STEPS.
