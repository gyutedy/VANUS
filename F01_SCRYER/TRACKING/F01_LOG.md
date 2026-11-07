# F01 SCRYER

2026-11-07 — silo cree. CODEBASE vide. Alias auto, pas d'ecran manuel.

2026-11-07 — PHASE-07 SCRYER.
- `CODEBASE/scryer.py` : aligne slates `vanus.slate.v1` → `vanus.match.v1`.
- `CODEBASE/run.py` : IN JSON (dossier ou fichier) → OUT un JSON par `match_key`. Enrichit `ARCHIVUM/aliases.json`.
- Cle : competition slug + date + HHMM kickoff + home/away normalises (minuscules, sans accents, sans FC/CF/AFC).
- Fenetre horaire ±45 min. Fuzzy `SequenceMatcher` seuil 0.90 seulement si ligue + horaire collent.
- Echec = `indexes.<id> = null` (tiroir vide). Athletic Club ≠ Athletic Bilbao. AC n'est pas un filler.
- Pas F02, pas snapshot, pas CELL.
