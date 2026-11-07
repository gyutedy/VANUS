# TODO — VANUS

Priorise. PHASE-12 F04 CIPHER Telegram done (2026-11-07).

---

## P0 — Doctrine (fait)

- [x] Nom VANUS + table des frégates
- [x] Arbre `IN/CODEBASE/OUT`
- [x] README, CONTINUATION, VERBUM, HERESIE
- [x] Contrats schemas (vides de donnees, pas de code)
- [x] Repo public GitHub
- [x] Plan 14 phases (`docs/05_IMPLEMENTATION.md`)

## Phases (une session = une phase)

Voir `docs/05_IMPLEMENTATION.md`. Ne pas enchainer.

- [x] PHASE-01 Harness
- [x] PHASE-02 F00 PredictLix
- [x] PHASE-03 F00 DailySportPick
- [x] PHASE-04 F00 MetaPred
- [x] PHASE-05 F00 FootInsights
- [x] PHASE-06 F00 BeSoccer + runner
- [x] PHASE-07 F01 SCRYER
- [x] PHASE-08 F02 snapshots + export
- [x] PHASE-09 F02 blogs
- [x] PHASE-10 F03 evolution + alertes
- [x] PHASE-11 F05 CELL
- [x] PHASE-12 F04 CIPHER
- [ ] PHASE-13 TARIEL + PA
- [ ] PHASE-14 E2E + CI pytest

## P1 — F00 INFOCYTE (PHASE-02 a 06)

- [x] Contrat `schema_slate.json` respecte par un premier parseur
- [x] PredictLix : page today, par competition, unite = match (fixture locale)
- [x] DailySportPick (fixture locale, OUT separe par index)
- [x] MetaPred (fixture locale, today only, par competition)
- [x] FootInsights (blog + tips)
- [x] BeSoccer : tentative GET honnete ; 406 = skip, log, pas de retry deguise
- [x] Delai inter-sites, User-Agent clair, robots.txt
- [x] Whitelist ligues dans `F00_INFOCYTE/IN/`

## P2 — F01 SCRYER

- [x] Cle composite : competition + date + creneau + domicile/exterieur + nom normalise
- [x] Table `ARCHIVUM/aliases.json` enrichie automatiquement
- [x] Fuzzy seulement si ligue + horaire collent, seuil haut
- [x] Echec = tiroir "pas trouve", jamais une fusion inventee

## P3 — F02 MNEMOS

- [x] Snapshot par match x source x marche x horodatage
- [x] Copies blog markdown + hash
- [x] Export JSON / CSV vers `ARCHIVUM/exports/`

## P4 — F03 SPECULUM

- [x] Timeline 10h → 12h → 14h, une ligne par index
- [x] Pinnacle : champ a part si deja dans la page
- [x] Alarme a 2 ; jackpot si toutes les sources trouvees
- [x] Absent ≠ vote ; meme issue (ex. domicile), pas le pick qui change de bord

## P5 — F05 CELL puis F04 CIPHER

- [x] Menus index + competition
- [x] Popup un match, accordéons
- [x] Tiroir evolution collectif
- [x] Telegram : alarme / jackpot, pas de rejeu du meme mouvement

## P6 — TARIEL + PA

- [ ] Poll delai reglable (defaut 2 h, plancher 15–30 min)
- [ ] Jusqu'au KO, option resserrer dans les 3 h avant
- [ ] `PA/pa_task.py` + `PA/pa_web.py` (squelettes, pas encore)

## Hors scope (ne pas faire)

- Scraper Pinnacle
- GitHub Actions comme nerf
- Ecran manuel d'alias
- Lier ce repo a Perturabo
- Mettre un tip dans un moteur de probabilites
