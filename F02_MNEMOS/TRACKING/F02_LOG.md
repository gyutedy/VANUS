# F02 MNEMOS

2026-11-07 — silo cree. CODEBASE vide. Snapshots / blogs / export a venir.

2026-11-07 — PHASE-08 snapshots + export.
- `CODEBASE/mnemos.py` : ingest match JSON → `ARCHIVUM/snapshots/snap_<key>.json`. Point = index × `captured_at` (odds/pick/score). Index null = pas de point.
- `CODEBASE/run.py` : IN match JSON → snapshots + copie OUT + export JSON/CSV `ARCHIVUM/exports/`.
- 2 polls → 2 points. Meme poll remplace le point. Export relit le store, pas de re-fetch.
- Pas blogs (PHASE-09). Pas F03.
