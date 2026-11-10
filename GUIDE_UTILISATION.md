# GUIDE D'UTILISATION — VANUS

Operateur : PythonAnywhere. Pas GitHub Actions (CI pytest seulement).

Flotte testable hors PA : `python3 -m pytest`.

---

## 1. Pieces

| Piece | Role | Commande |
|---|---|---|
| Tests | fixtures locales, pas de reseau | `python3 -m pytest` |
| Tache planifiee | un reveil TARIEL | `python3 PA/pa_task.py` |
| Orchestrateur | une passe | `python3 TARIEL/CODEBASE/run.py --once` |
| Web app | WSGI → F05 CELL | `PA/pa_web.py` (`application`) |
| Telegram | env hote | `VANUS_TELEGRAM_TOKEN` + `VANUS_TELEGRAM_CHAT_ID` |

## 2. Rythme

- Defaut : `poll_minutes` 120 dans `F00_INFOCYTE/IN/sources.json`.
- Plancher 30 min. TARIEL s'arrete apres le KO.
- Preview : menus index → competition → matchs ; popup un match.

## 3. Comment lire la salle (CELL)

1. Choisir un **index** (PredictLix, DailySportPick, MetaPred, …).
2. Choisir une **competition**.
3. Voir **tous les matchs du jour** de cette competition.
4. Cliquer un match → **popup unique**.
5. Accordéons : un ouvert a la fois.
6. Marche par defaut : 1X2. Changeable dans la popup.
7. Tiroir evolution : une ligne par index. Pinnacle en reference si presente.

Dump HTML local :

```
python3 F05_CELL/CODEBASE/run.py --in F05_CELL/IN --out F05_CELL/OUT
```

## 4. Alertes

- 2 sources dans le meme sens → alarme (bandeau CELL + Telegram).
- Toutes les sources trouvees d'accord → jackpot.
- Une source absente n'est pas un vote.
- Token absent : log, pas crash. Jamais de secret dans git.

```
python3 F04_CIPHER/CODEBASE/run.py --in F03_SPECULUM/OUT --out F04_CIPHER/OUT
```

## 5. Export

`ARCHIVUM/exports/` — JSON / CSV pour tes calculs **sur ta copie**. Pas de re-scrape pour calculer.

## 5b. Publier le signal pour un autre projet

L'export est ecrit a chaque poll dans `SHARED/OUT/signals/` :

    SHARED/OUT/signals/latest.json          vue courante, tous matchs
    SHARED/OUT/signals/signals_YYYY-MM-DD.json   archive du jour

Sur PythonAnywhere, exposer le dossier en statique :

  Web -> Static files
    URL  : /signals/
    Path : /home/<user>/VANUS/SHARED/OUT/signals

L'URL a donner au consommateur est donc :

  https://<user>.pythonanywhere.com/signals/latest.json

Verification depuis n'importe ou :

  curl -s https://<user>.pythonanywhere.com/signals/latest.json | head -30

Le fichier ne contient aucune donnee privee : ce sont des cotes publiques
deja affichees sur six sites publics. Aucun jeton. Aucun compte.

Si un index n'a pas parle sur un match, son champ vaut `null`. C'est
volontaire : `absent != consensus` (VERBUM VII, HERESIE #15).

## 6. Ce que tu ne fais pas

- Relier les alias a la main.
- Lancer un crawl.
- Demander a VANUS de placer un pari.
- Cron GitHub de capture.

## 7. Reprise a froid

Lire `CONTINUATION.md`, puis `TODO.md`.

Greffe : `CONTRACTS/` + `SHARED/OUT/signals/`. CELL/CIPHER lisent encore `F03_SPECULUM/OUT/`.
