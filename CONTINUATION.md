# CONTINUATION — Reprise du Temple (VANUS)

> **LIRE CE FICHIER EN PREMIER** si vous arrivez dans ce repo a froid.
> Il dit exactement ou le travail s'est arrete et quoi faire ensuite.

---

## DERNIERE MISE A JOUR

**Date** : 2026-11-07
**Etat** : PHASE-01 harness **done**. Aucun parseur. Prochaine = PHASE-02 (PredictLix) puis STOP.
**Runtime cible** : PythonAnywhere (pas GitHub Actions).
**Repo** : https://github.com/gyutedy/VANUS — public, seul, greffable. Pas lie a Perturabo.
**Plan** : `docs/05_IMPLEMENTATION.md` — une phase par session, puis STOP.

---

## 1. CE QUI EXISTE

- Arbre des frégates (`F00` → `F05`, `TARIEL`, `PA`, `SHARED`)
- Doctrine : `README.md`, `VERBUM.md`, `HERESIE.md`
- Contrats JSON (schemas) dans `CONTRACTS/`
- Journaux vides dans `TRACKING/` et chaque `Fxx/TRACKING/`
- Whitelist sources (intention) dans `ARCHIVUM/rules/whitelist_sources.md`
- `TODO.md` : chantier priorise
- `GUIDE_UTILISATION.md` : ce que l'operateur fera sur PythonAnywhere
- Guides `docs/01` a `docs/05`
- `VANUS_CUSTOS.py` (seul a ecrire `liber_vanus.json`)
- `pytest` + fixtures JSON golden (`tests/`)
- `liber_vanus.json` status `phase_01_harness`

## 2. CE QUI N'EXISTE PAS (volontaire)

- Aucun parseur HTML
- Aucun `tariel.py` / `pa_task.py` / `pa_web.py`
- Aucune dependance pip metier (hors pytest/jsonschema)
- Aucun secret, aucun jeton

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

PHASE-02 — F00 PredictLix. Fixture HTML locale, un site, `schema_slate.json`. Puis STOP. Pas DSP.

Ordre impose, une frégate a la fois :

1. `CONTRACTS/` — ne plus les bouger sans version
2. F00 INFOCYTE — un site (PredictLix) puis les autres
3. F01 SCRYER — cle composite ligue + horaire + noms
4. F02 MNEMOS — snapshot SQLite / fichiers
5. F03 SPECULUM — evolution + bandeau consensus
6. F05 CELL — preview lisible
7. F04 CIPHER — Telegram
8. TARIEL + `PA/` — coller sur PythonAnywhere

Ne pas commencer par la preview. CELL ne calcule rien.

## 5. OU SONT LES TROUS

| Trou | Fichier |
|---|---|
| Chantier ouvert | `TODO.md` |
| Hotes / poll | `docs/01_PYTHONANYWHERE.md` |
| UX popup | `docs/02_POPUP_ACCORDEONS.md` |
| Alias | `docs/03_ALIAS.md` |
| Alertes | `docs/04_ALERTES_TELEGRAM.md` |
| 14 phases | `docs/05_IMPLEMENTATION.md` |

---

*Temple Vanus — la lecture precede le signal.*
