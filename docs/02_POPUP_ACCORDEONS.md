# 02 — Popup et accordéons (CELL)

## Unites

- Menu = un **index** (PredictLix, DailySportPick, MetaPred, …).
- Sous-menu = une **competition** du jour.
- Ligne = un **match**.
- Popup = **ce** match. Pas une liste.

## Accordéons

Un ouvert a la fois. Pas de `<select>` empiles.

1. En-tete fige : competition, heure, score s'il existe.
2. Tiroir par index : leur fiche (pick, cotes, %, EV). Vide = "pas trouve".
3. Tiroir detail dans l'index ouvert.
4. Tiroir **evolution** : une vue, N lignes, meme axe horaire.

## Marche

Defaut a l'ouverture : 1X2. Changeable dans la popup. Pas de favori global.
Le meme marche s'applique a tous les tiroirs, sinon on compare des pommes.

## Evolution

- Une ligne PredictLix, une DSP, une MetaPred, Pinnacle en reference si deja la.
- Table des points + SVG interne (polyline / cercle). Pas de lib, pas de son.
- Un seul releve = point seul + « attente 2e releve ». Courbe a partir de 2 points.
- Bandeau : 2 dans le meme sens = alarme ; toutes = jackpot.
- Absent ≠ vote.

## Skin

- Plaque Officio Assassinorum / TEMPLE VANUS / CELL.
- Accueil = dalles index, pas une liste nue.
- Charte sombre (fond #0c0b09, or #c4a35a). HTML genere par `cell.py`. Pas de HTML OUT dans git.
