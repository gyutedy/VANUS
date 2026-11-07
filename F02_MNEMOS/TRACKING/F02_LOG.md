# F02 MNEMOS

2026-11-07 — silo cree. CODEBASE vide. Snapshots / blogs / export a venir.

2026-11-07 — PHASE-08 snapshots + export.
- `CODEBASE/mnemos.py` : ingest match JSON → `ARCHIVUM/snapshots/snap_<key>.json`. Point = index × `captured_at` (odds/pick/score). Index null = pas de point.
- `CODEBASE/run.py` : IN match JSON → snapshots + copie OUT + export JSON/CSV `ARCHIVUM/exports/`.
- 2 polls → 2 points. Meme poll remplace le point. Export relit le store, pas de re-fetch.
- Pas blogs (PHASE-09). Pas F03.

2026-11-07 — PHASE-09 blogs.
- `CODEBASE/blogs.py` : copie locale markdown sous `ARCHIVUM/blogs/<index>/<slug>.md` + hash sha256 + `vanus.blog.v1`.
- `run.py --mode blogs` : IN article JSON (url/title/body) → copie + meta OUT. Pas de GET reseau.
- 1er run `new` ; 2e identique `unchanged` ; contenu change `updated`. Pas un miroir public.
- Pas F03.
