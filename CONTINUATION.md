# CONTINUATION — Reprise du Temple (VANUS)

> **LIRE CE FICHIER EN PREMIER** si vous arrivez dans ce repo a froid.
> Il dit exactement ou le travail s'est arrete et quoi faire ensuite.

---

## DERNIERE MISE A JOUR

**Date** : 2026-11-10
**Etat** : PHASE-16 done. `signals_export.py` + `tests/test_signal.py`. `run.py` / TARIEL non touches. Prochaine session = PHASE-17 seulement.
**Runtime cible** : PythonAnywhere (pas GitHub Actions).
**Repo** : https://github.com/gyutedy/VANUS — public, seul, greffable. Pas lie a Perturabo.
**Plan 01-14** : `docs/05_IMPLEMENTATION.md`
**Plan 15-17** : `docs/06_SIGNAL.md` — une phase par session, puis STOP.

---

## 1. CE QUI EXISTE

- Arbre des frégates (`F00` → `F05`, `TARIEL`, `PA`, `SHARED`)
- Doctrine : `README.md`, `VERBUM.md`, `HERESIE.md`
- Contrats JSON (schemas) dans `CONTRACTS/`
- Journaux dans `TRACKING/` et chaque `Fxx/TRACKING/`
- Whitelist sources dans `ARCHIVUM/rules/whitelist_sources.md`
- `TODO.md` : chantier priorise
- `GUIDE_UTILISATION.md` : ce que l'operateur fera sur PythonAnywhere
- Guides `docs/01` a `docs/05`
- `VANUS_CUSTOS.py` (seul a ecrire `liber_vanus.json`)
- `pytest` + fixtures JSON golden + HTML PredictLix + DSP + MetaPred + FootInsights + BeSoccer + Vitibet (`tests/`)
- `F00_INFOCYTE/CODEBASE/predictlix.py` + `dailysportpick.py` + `metapred.py` + `footinsights.py` + `besoccer.py` + `vitibet.py` + `run.py` + `runner.py`
- `F01_SCRYER/CODEBASE/scryer.py` + `run.py` (cle composite, aliases.json auto, fuzzy seuil 0.90)
- `F02_MNEMOS/CODEBASE/mnemos.py` + `blogs.py` + `run.py` (snapshots, export JSON/CSV, copie blogs)
- `F03_SPECULUM/CODEBASE/speculum.py` + `run.py` (evolution + alertes, fingerprint) + `signals_export.py` (pas encore branche)
- `F05_CELL/CODEBASE/cell.py` + `run.py` (menus, popup, skin Temple Vanus, SVG evolution)
- `F04_CIPHER/CODEBASE/cipher.py` + `run.py` (Telegram, fingerprint, token env)
- `TARIEL/CODEBASE/tariel.py` + `gates.py` + `run.py` (poll, subprocess, portes)
- `PA/pa_task.py` + `PA/pa_web.py` (un reveil ; WSGI → F05)
- `.github/workflows/pytest.yml` (pytest only, pas de cron)
- `liber_vanus.json` status `harness_ready`

## 2. CE QUI N'EXISTE PAS (volontaire)

- Aucun GET reseau dans les tests (fixtures locales ; 406 mocke)
- Aucun parseur hors F00
- Aucune dependance pip metier (hors pytest/jsonschema)
- Aucun secret, aucun jeton
- Aucun cron GitHub de capture

## 3. DECISIONS FIGEES

Voir `VERBUM.md` et `HERESIE.md`. Resume :

1. Repo seul, pas un monde Perturabo. Greffe future = capteur, pas un moteur de `p`.
2. Une sous-frégate = `IN/ → CODEBASE/ → OUT/` + contrat. Zero appel direct.
3. Alias auto. Pas d'ecran manuel. Tiroir vide si un index ne colle pas.
4. Popup = un match. Accordéons. Evolution = une vue, N lignes.
5. Alarme a 2 sources dans le meme sens. Jackpot si toutes. Telegram + CELL.
6. Pinnacle seulement si un index la montre deja. Ligne de reference, pas un index de tips.
7. 406 BeSoccer = skip. Pas de deguisement.
8. PythonAnywhere : poll + preview. Delai reglable, defaut 2 h.

## 4. PROCHAINE ETAPE

14 phases closes. Chantier SIGNAL ouvert. **PHASE-15 en premier**, puis STOP.

Ordre impose (`docs/06_SIGNAL.md`) :

1. PHASE-15 — `CONTRACTS/schema_signal.json` + golden + `test_contracts` — **fait**
2. PHASE-16 — `F03_SPECULUM/CODEBASE/signals_export.py` + `tests/test_signal.py` — **fait**
3. PHASE-17 — `--signal-out` dans `run.py` / commande F03 TARIEL + docs PA + E2E — **a faire**

Coller le code du cahier 2026-11-09. Ne pas inventer. Ne pas toucher F00–F02, F04, F05, CIPHER. Ne pas coder PARI ici.

Ne pas commencer par TARIEL. CELL ne calcule rien.

## 5. OU SONT LES TROUS

| Trou | Fichier |
|---|---|
| Chantier ouvert | `TODO.md` |
| Hotes / poll | `docs/01_PYTHONANYWHERE.md` |
| UX popup | `docs/02_POPUP_ACCORDEONS.md` |
| Alias | `docs/03_ALIAS.md` |
| Alertes | `docs/04_ALERTES_TELEGRAM.md` |
| 14 phases | `docs/05_IMPLEMENTATION.md` |
| SIGNAL 15-17 | `docs/06_SIGNAL.md` |

---

*Temple Vanus — la lecture precede le signal.*
