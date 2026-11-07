# F01 SCRYER

2026-11-07 — silo cree. CODEBASE vide. Alias auto, pas d'ecran manuel.

2026-11-07 — PHASE-07 SCRYER.
- `CODEBASE/scryer.py` : aligne slates `vanus.slate.v1` → `vanus.match.v1`.
- `CODEBASE/run.py` : IN JSON (dossier ou fichier) → OUT un JSON par `match_key`. Enrichit `ARCHIVUM/aliases.json`.
- Cle : competition slug + date + HHMM kickoff + home/away normalises (minuscules, sans accents, sans FC/CF/AFC).
- Fenetre horaire ±45 min. Fuzzy `SequenceMatcher` seuil 0.90 seulement si ligue + horaire collent.
- Echec = `indexes.<id> = null` (tiroir vide). Athletic Club ≠ Athletic Bilbao. AC n'est pas un filler.
- Pas F02, pas snapshot, pas CELL.

2026-11-07 — collage live F00.
- Slug ligue : peel pays (England/Angleterre/…) + defaut Premier League → england. Ghana PL reste ghana.
- Kickoff T00:00:00Z = heure absente, meme jour. Horaire reel remplace minuit.
- Noms : Leeds United / Tottenham Hotspur / Nott'm Forest / Man City collent si tokens compatibles. Athletic Club ≠ Athletic Bilbao.

2026-11-07 — 2e run F01 (dump F00 live, slugs canon).
- OUT mélange ancien + nouveau (pas de delete) : 3245 fichiers. Nouveaux slugs : Fulham–Newcastle n=4 ; Leeds–Tottenham 12:30 n=3 ; Arsenal–Hull 15:00 n=3.
- Championship : 11 fiches n=3 (PredictLix + FootInsights + Vitibet).
- Couverture indexes (tous fichiers, dont stale) : vitibet 2261, footinsights 668, predictlix 641, dailysportpick 12.
- aliases.json : 14 paires (leeds/leeds united, stoke/stoke city, …).
- Trou restant : Nott'm Forest vs Man City 17:30 (FootInsights seul) ≠ Nottingham Forest vs Manchester City 20:30 (PredictLix+Vitibet) — delta 3 h, hors ±45 min, aucun minuit. F01 n'aligne pas.
