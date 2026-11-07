# GUIDE D'UTILISATION — VANUS

Operateur : PythonAnywhere. Pas GitHub Actions.

Ce guide decrit **ce qui sera**. Rien n'est encore deploye (docs only).

---

## 1. Ce que tu auras

| Piece | Role |
|---|---|
| Tache planifiee | `PA/pa_task.py` reveille TARIEL (defaut toutes les 2 h) |
| Web app | `PA/pa_web.py` sert F05 CELL |
| Preview | menus index → competition → matchs ; popup un match |
| Telegram | alarme (2 sources) / jackpot (toutes) |

## 2. Rythme

- Defaut : lire quelques minutes, dormir ~2 h, jusqu'au coup d'envoi.
- Delai reglable dans `F00_INFOCYTE/IN/` (plancher 15–30 min).
- Option future : resserrer dans les 3 h avant KO.

## 3. Comment lire la salle (CELL)

1. Choisir un **index** (PredictLix, DailySportPick, MetaPred, …).
2. Choisir une **competition** (Liga, J1, C1, …).
3. Voir **tous les matchs du jour** de cette competition, comme chez eux.
4. Cliquer un match → **popup unique**.
5. Accordéons : un ouvert a la fois (fiche d'un index, detail, evolution).
6. Marche par defaut : 1X2. Changeable dans la popup.
7. Tiroir evolution : une ligne par index, meme axe horaire. Pinnacle en reference si presente.

## 4. Alertes

- 2 sources dans le meme sens → alarme (bandeau CELL + Telegram).
- Toutes les sources trouvees d'accord → jackpot (plus fort).
- Une source absente n'est pas un vote.
- Pinnacle dans le meme sens = jackpot "juge". Sans Pinnacle = jackpot "sites", plus petit.

## 5. Export

`ARCHIVUM/exports/` — JSON / CSV pour tes calculs **sur ta copie**. Pas de re-scrape pour calculer.

## 6. Ce que tu ne fais pas

- Relier les alias a la main.
- Lancer un crawl.
- Demander a VANUS de placer un pari.

## 7. Reprise a froid

Lire `CONTINUATION.md`, puis `TODO.md`.
