# VANUS

> *L'ennemi connu est deja battu. Encore faut-il l'avoir lu.*
> — Temple Vanus, Officio Assassinorum

Repo seul. Pas un monde Perturabo. Construit en frégate + sous-frégates, greffable plus tard comme capteur (même super-capteur F00) dans un autre projet. Aujourd'hui : zéro import Perturabo.

VANUS **lit** des pages publiques de pronostics / cotes / blogs. Il archive, aligne, signale. Il ne parie pas. Il ne contourne pas.

---

## POSITIONNEMENT

```
F00 INFOCYTE     capture HTML public (index whitelist)
F01 SCRYER       aligne un match entre index (alias auto)
F02 MNEMOS       snapshots, copies de blogs, export
F03 SPECULUM     evolution des cotes + Pinnacle-si-deja-la + consensus
F04 CIPHER       Telegram (alarme a 2, jackpot si tous)
F05 CELL         preview : menus ligue, popup accordéons
TARIEL           orchestre, ne calcule pas
PA               nerf PythonAnywhere (tache planifiee + WSGI)
```

Un autre projet n'a pas besoin de VANUS entier. Il lit `CONTRACTS/` + `F03_SPECULUM/OUT/`.

---

## LES FRÉGATES

| Code | Nom | Role | Output (contrat) |
|---|---|---|---|
| F00 | INFOCYTE | Capture des index, 1 module / site | `schema_slate.json` |
| F01 | SCRYER | Cle match, alias auto, pas d'ecran manuel | `schema_match.json` |
| F02 | MNEMOS | Snapshots, blogs, export JSON/CSV | snapshots + `schema_blog.json` |
| F03 | SPECULUM | Evolution 10h→12h→14h, consensus, Pinnacle-si-la | `schema_evolution.json` + `schema_alert.json` |
| F04 | CIPHER | Telegram | message alerte / jackpot |
| F05 | CELL | Preview : ligues, slate, popup | HTML, lit seulement OUT/ARCHIVUM |
| — | TARIEL | Poll delai reglable, jusqu'au KO | — |
| — | VANUS_CUSTOS | Seul a toucher `liber_vanus.json` | fleet_status |

Chaque frégate = `IN/ → CODEBASE/ → OUT/` + son contrat. La voisine ne lit que le JSON.

---

## PREVIEW (CELL)

- Menus = index. Clic PredictLix / DailySportPick / MetaPred → leur slate du jour, par competition.
- Popup = **un** match. Accordéons, un ouvert a la fois.
- Tiroir evolution = **une** vue, N lignes (une par index + Pinnacle en reference si deja presente dans une page).
- Marche par defaut a l'ouverture : 1X2. Changeable dans la popup. Pas de favori global.
- 2 sources dans le meme sens = alarme. Toutes = jackpot. Absent ≠ consensus.

---

## RUNTIME

Pas GitHub Actions. **PythonAnywhere** :

- `PA/pa_task.py` — tache planifiee → TARIEL
- `PA/pa_web.py` — WSGI → F05 seulement

Delai de poll reglable (defaut 2 h, plancher 30 min). Jusqu'au coup d'envoi.
CI GitHub : pytest only (pas de cron de capture).

---

## GREFFE

| On emporte | On laisse |
|---|---|
| `CONTRACTS/` + `F03_SPECULUM/OUT/` | F05 si pas d'ecran |
| `F00_INFOCYTE/` si on change de sources | `PA/` si autre hote |
| Le repo entier | Rien de Perturabo (il n'y en a pas) |

---

## DOCS

| Fichier | Role |
|---|---|
| `CONTINUATION.md` | Lire en premier a froid |
| `TODO.md` | Chantier ouvert |
| `VERBUM.md` | Axiomes |
| `HERESIE.md` | Interdits |
| `GUIDE_UTILISATION.md` | Operateur PythonAnywhere |
| `TRACKING/` | Journaux |
| `docs/` | Guides numerotes |
| `docs/05_IMPLEMENTATION.md` | 14 phases, une par session |
| `VANUS_CUSTOS.py` | Seul ecrivain de `liber_vanus.json` |

Tests : `python3 -m pytest` (fixtures locales, pas de reseau).

---

*Temple Vanus — on observe, on archive, on signale.*
