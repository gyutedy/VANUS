# 06 — Plan SIGNAL (PHASE-15 a 17)

Source de verite pour le chantier VANUS du cahier 2026-11-09.
Une phase = une session. Coder uniquement la phase courante. Puis STOP.

Lire aussi : `CONTINUATION.md`, `VERBUM.md`, `HERESIE.md`, `TODO.md`, `docs/05_IMPLEMENTATION.md`.

---

## Perimetre

VANUS seulement. PARI (Dixon-Coles, `vanus_fetch`, `vanus_gate`, Telegram PARI) = autre depot, autre sandbox.

Objectif : passer d'observateur a **fournisseur de signaux**.
La sortie n'est plus N fichiers `evolution_*.json` / `alert_*.json` (ceux-la restent pour CELL et CIPHER).
On **ajoute** un export agrege `vanus.signal.v1` dans `SHARED/OUT/signals/`.

Greffe future : un autre projet lit `CONTRACTS/` + `SHARED/OUT/signals/latest.json`.
VANUS n'importe rien de PARI. VANUS n'a aucun client HTTP vers PARI.

## Ce que ce plan ne fait pas

- Pas F00, F01, F02, F05, CELL skin, CIPHER, PA web CELL.
- Pas de changement du format `evolution_*.json` / `alert_*.json`.
- Pas de scrape Pinnacle.
- Pas d'import Perturabo.
- Pas de `p` calcule. Un pick reste une observation (HERESIE #7).
- Pas de fichier nomme `signal.py` (collision stdlib). Module = `signals_export.py`.

## Ordre impose

```
PHASE-15  contrat schema_signal + tests contrat     puis STOP
PHASE-16  signals_export.py + tests signal          puis STOP
PHASE-17  branchement run.py / TARIEL + docs PA     puis STOP
```

Interdit d'enchainer. Interdit de commencer par TARIEL.

## Regle d'une phase (rappel)

1. Lire `CONTINUATION.md` + ce fichier + la phase courante.
2. Coder **uniquement** cette phase.
3. `python3 -m pytest -q` (fixtures locales, pas de reseau).
4. Maj `CONTINUATION.md`, `TODO.md`, `TRACKING/VANUS_LOG.md`, log de la fregate.
5. Commit + push. Message : `phase-NN: …`
6. **STOP.**

---

## PHASE-15 — Contrat `vanus.signal.v1`

**But :** le schema existe, pytest le valide, zero code metier.

### Creer `CONTRACTS/schema_signal.json`

Coller le JSON du cahier B.2 (contrat `vanus.signal.v1`). Points figes :

- `required` : `contract`, `generated_at`, `slate_date`, `matches`
- `contract` const = `vanus.signal.v1`
- `indexes_vus` enum = predictlix, dailysportpick, metapred, footinsights, besoccer, vitibet
- un match = une entree ; marches = champs (`1x2`, `ou_2_5`, `btts`, `mt`)
- index muet = `null`, jamais 0
- `reference.sharp` nullable (Pinnacle seulement si deja la)
- `consensus.niveau` enum : `aucun` | `isole` | `alarme` | `jackpot`
- `couverture.niveaux` enum : `faible` | `moyenne` | `haute`

### Creer `tests/fixtures/json/signal.json`

Instance golden minimale valide :

- `contract` = `vanus.signal.v1`
- un match, un index present, les autres `null`
- `consensus.niveau` = `isole`
- `reference.sharp` = `null`
- `holes` peut contenir `cotes_ou_2_5`

### Modifier `tests/test_contracts.py`

Ajouter `schema_signal.json` a `SCHEMAS` et `("signal.json", "schema_signal.json")` a `GOLDEN`.

### Modifier `CONTRACTS/README.md`

Ajouter la ligne :

```
| `schema_signal.json` | F03 SPECULUM (`signals_export.py`) | greffe externe, PARI |
```

Et le rappel : `schema_signal` n'est PAS une probabilite. Un `pick` reste une observation. Aucun consommateur ne le convertit en `p` (HERESIE #7).

### Docs

- `CONTINUATION.md` : PHASE-15 en cours / done. Prochaine = 16.
- `TODO.md` : cocher PHASE-15, ouvrir 16-17.
- `TRACKING/VANUS_LOG.md` + `F03_SPECULUM/TRACKING/F03_LOG.md`
- `docs/05_IMPLEMENTATION.md` : pointer vers ce fichier pour 15-17.

### Tests

```
python3 -m pytest tests/test_contracts.py -q
python3 -m pytest -q
```

### Exit

Schema valide. Golden passe. Zero `signals_export.py`. Commit `phase-15: contrat vanus.signal.v1`. Push. STOP.

**Etat 2026-11-10 : DONE.**

---

## PHASE-16 — `signals_export.py`

**But :** agreger les snapshots F02 en `vanus.signal.v1`. Pas de branchement TARIEL.

### Creer `F03_SPECULUM/CODEBASE/signals_export.py`

Coller le module du cahier B.2 **tel quel**, en decodant les entites HTML (`&gt;` → `>`, `&lt;` → `<`).

Nom du fichier = `signals_export.py` (pas `signal.py`).

Regles tenues dans le code :

- absent = `null`, jamais 0
- Pinnacle seulement si un point existant la porte (`pinnacle` / `pin` / `pn`)
- consensus : 2 indexes alignes = `alarme` ; tous les 6 presents d'accord = `jackpot` ; 1 seul = `isole`
- aucune probabilite
- ecriture atomique `*.tmp` puis `replace`
- sorties : `signals_YYYY-MM-DD.json` + `latest.json`

CLI (testable hors TARIEL) :

```
python3 F03_SPECULUM/CODEBASE/signals_export.py \
  --in F02_MNEMOS/OUT \
  --out SHARED/OUT/signals \
  --slate YYYY-MM-DD
```

Defaut `--in` = `F02_MNEMOS/OUT`. Defaut `--out` = `SHARED/OUT/signals`.

### Creer `tests/test_signal.py`

Meme cas que le cahier, **en pytest** (`assert`, pas le harnais `check()`). Cas obligatoires :

1. index muet → `null` ; marche O/U absent → trou `cotes_ou_2_5`
2. 2 picks home (predictlix + metapred) → `consensus.niveau == "alarme"`, `n == 2`
3. 1 seul index → `isole`, jamais `alarme`
4. Pinnacle absente → `reference.sharp is None` et `source is None`
5. Pinnacle deja dans odds → `sharp == 1.95`
6. 2 points horodates → `ouvert.home == 2.10`, `cloture.home == 1.85`
7. `aggregate` ecrit `signals_YYYY-MM-DD.json` + `latest.json` + `contract == vanus.signal.v1`
8. `canon_pick("peut-etre") is None` ; `canon_pick("Plus") == "over_2_5"`

Ne pas importer F00–F02–F04–F05. Ne pas fetcher.

Charger le module comme les autres tests (`importlib` depuis `F03_SPECULUM/CODEBASE`), pour rester coherent avec `test_speculum.py` / `test_cell.py`.

### Docs

- `F03_SPECULUM/TRACKING/F03_LOG.md`
- `CONTINUATION.md` : PHASE-16 done. Prochaine = 17.
- `TODO.md`, `TRACKING/VANUS_LOG.md`

### Tests

```
python3 -m pytest tests/test_signal.py tests/test_speculum.py tests/test_contracts.py -q
python3 -m pytest -q
```

Les `evolution_*.json` / `alert_*.json` ne changent pas (fichier non touche : `speculum.py`).

### Exit

Tous les cas signal verts. Suite pytest verte. `run.py` et `tariel.py` **non modifies**. Commit `phase-16: signals_export vanus.signal.v1`. Push. STOP.

**Etat 2026-11-10 : DONE.**

---

## PHASE-17 — Branchement + publication

**But :** l'export tourne a chaque poll. Docs PA. E2E. `latest.json` ne se perime pas.

### Modifier `F03_SPECULUM/CODEBASE/run.py`

Apres la boucle existante (evolution + alert) et `save_seen`, ajouter `--signal-out` (defaut = `SHARED/OUT/signals`, chaine vide = desactive) :

```
parser.add_argument(
    "--signal-out",
    default=str(FRIGATE.parent / "SHARED" / "OUT" / "signals"),
    help="export vanus.signal.v1 (vide pour desactiver)",
)

# apres save_seen(...)
if args.signal_out:
    import signals_export as _sigx
    snaps = load_snapshots(src)
    blob, _w = _sigx.aggregate(snaps, Path(args.signal_out))
    print(f"[SIGNAL] {len(blob['matches'])} match(s) -> {args.signal_out}")
```

Ne pas toucher a la boucle evolution/alert.

### Modifier `TARIEL/CODEBASE/tariel.py`

Ne **pas** ajouter une etape `F03_SIGNAL` separee (doublerait F03, casserait `test_tariel` ordre).

Ajouter `--signal-out` a la commande **existante** `F03_SPECULUM` dans `default_commands` :

```
"--signal-out", str(root / "SHARED" / "OUT" / "signals"),
```

`LECTURE_STEPS` inchange. `ALERTE_STEPS` inchange (l'export ne notifie pas).

Creer `SHARED/OUT/signals/.gitkeep` (dossier versionne, JSON produits ignores s'ils le sont deja par `.gitignore` ; sinon ne pas committer les JSON de sortie).

### Modifier `tests/test_e2e.py`

Apres le run F03, passer `--signal-out` vers un tmp, charger `latest.json`, `validate_instance(..., "schema_signal.json")`.
Les asserts evolution/alert existants restent.

### Modifier `tests/test_tariel.py` seulement si l'ordre des steps change. Il ne doit pas changer.

### Docs operateur

Ajouter a `GUIDE_UTILISATION.md` la section du cahier C (publication) :

```
## Publier le signal pour un autre projet

L'export est ecrit a chaque poll dans `SHARED/OUT/signals/` :

    SHARED/OUT/signals/latest.json
    SHARED/OUT/signals/signals_YYYY-MM-DD.json

Sur PythonAnywhere, exposer le dossier en statique :

  Web -> Static files
    URL  : /signals/
    Path : /home/<user>/VANUS/SHARED/OUT/signals

URL consommateur :

  https://<user>.pythonanywhere.com/signals/latest.json

Verification :

  curl -s https://<user>.pythonanywhere.com/signals/latest.json | head -30

Pas de jeton. Index muet = null. absent != consensus.
```

Ajouter la meme note courte dans `docs/01_PYTHONANYWHERE.md`.

Mettre a jour `README.md` : greffe = `CONTRACTS/` + `SHARED/OUT/signals/` (F03 OUT reste pour CELL/CIPHER).

### CONTINUATION / TODO / logs

- `CONTINUATION.md` : PHASE-17 done. Hors session = operer PA (static `/signals/`). Ne pas reouvrir une phase sans besoin.
- `TODO.md` : 15-17 coches.
- `TRACKING/VANUS_LOG.md`, `F03_LOG.md`, `TARIEL_LOG.md`
- `docs/05_IMPLEMENTATION.md` : 15-17 closes.

### Tests

```
python3 -m pytest -q
python3 F03_SPECULUM/CODEBASE/run.py --in F02_MNEMOS/OUT --out F03_SPECULUM/OUT \
        --signal-out SHARED/OUT/signals
ls -la SHARED/OUT/signals/
```

(Le run live n'est pas obligatoire si F02 OUT est vide ; pytest E2E suffit.)

### Criteres d'acceptation (cahier B + C cote VANUS)

1. `latest.json` porte `contract: "vanus.signal.v1"` et `generated_at` ISO.
2. Index muet = `null`, jamais `{}` ni `0`.
3. Un seul index → `consensus.niveau = "isole"`, jamais `"alarme"`.
4. `reference.sharp` = `null` si aucune page ne porte Pinnacle.
5. `evolution_*.json` / `alert_*.json` inchanges pour les memes entrees. Tests existants verts.
6. `grep -r "perturabo" --include='*.py'` ne renvoie rien hors commentaire de doctrine.
7. L'export ne notifie pas Telegram. CIPHER inchange.
8. Aucun secret dans git.

### Exit

Pytest vert. Commit `phase-17: poll F03 exporte vanus.signal.v1`. Push. STOP.

---

## Hors VANUS (ne pas coder ici)

| Piece | Depot |
|---|---|
| `vanus_fetch.py` | PARI `F03_FORGEWARD` |
| `vanus_gate.py` | PARI `F03_FORGEWARD` |
| `PARI_VANUS_URL` | PARI `env_pari` |
| Dixon-Coles / gel tickets | PARI |

Le pont est un **fichier publie** + un **lecteur qui le tire**. VANUS publie. PARI tire. Telegram n'est pas un bus.

## Interdits (rappel cahier D.2)

- Un pronostic d'index entre dans un `p`
- Une cote manquante comblee par une estimation
- Pinnacle scrapee
- Import Perturabo dans VANUS
- Secret dans git
- Enchainer les phases
