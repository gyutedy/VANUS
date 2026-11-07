# TODO — VANUS

Priorise. Rien de ceci n'est commence (docs only, 2026-11-07).

---

## P0 — Doctrine (fait)

- [x] Nom VANUS + table des frégates
- [x] Arbre `IN/CODEBASE/OUT`
- [x] README, CONTINUATION, VERBUM, HERESIE
- [x] Contrats schemas (vides de donnees, pas de code)
- [x] Repo public GitHub

## P1 — F00 INFOCYTE (premier code, plus tard)

- [ ] Contrat `schema_slate.json` respecte par un premier parseur
- [ ] PredictLix : page today, par competition, unite = match
- [ ] DailySportPick, MetaPred, FootInsights (blog + tips)
- [ ] BeSoccer : tentative GET honnete ; 406 = skip, log, pas de retry deguise
- [ ] Delai inter-sites, User-Agent clair, robots.txt
- [ ] Whitelist ligues dans `F00_INFOCYTE/IN/`

## P2 — F01 SCRYER

- [ ] Cle composite : competition + date + creneau + domicile/exterieur + nom normalise
- [ ] Table `ARCHIVUM/aliases.json` enrichie automatiquement
- [ ] Fuzzy seulement si ligue + horaire collent, seuil haut
- [ ] Echec = tiroir "pas trouve", jamais une fusion inventee

## P3 — F02 MNEMOS

- [ ] Snapshot par match x source x marche x horodatage
- [ ] Copies blog markdown + hash
- [ ] Export JSON / CSV vers `ARCHIVUM/exports/`

## P4 — F03 SPECULUM

- [ ] Timeline 10h → 12h → 14h, une ligne par index
- [ ] Pinnacle : champ a part si deja dans la page
- [ ] Alarme a 2 ; jackpot si toutes les sources trouvees
- [ ] Absent ≠ vote ; meme issue (ex. domicile), pas le pick qui change de bord

## P5 — F05 CELL puis F04 CIPHER

- [ ] Menus index + competition
- [ ] Popup un match, accordéons
- [ ] Tiroir evolution collectif
- [ ] Telegram : alarme / jackpot, pas de rejeu du meme mouvement

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
