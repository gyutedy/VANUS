# 04 — Alertes et Telegram (SPECULUM → CIPHER)

## Niveaux

| Niveau | Condition | CELL | Telegram |
|---|---|---|---|
| alarme | ≥ 2 sources trouvees, meme sens | badge + surbrillance | ping |
| jackpot | toutes les sources trouvees, meme sens | bandeau prioritaire | ping plus fort |

## Juge Pinnacle

- Pinnacle seulement si un index la montre deja.
- Toutes + Pinnacle meme sens = jackpot reel.
- Toutes sans Pinnacle = jackpot "sites", plus petit.
- Sites descendent, Pinnacle immobile = alarme plus faible.

## Idempotence

`fingerprint` dans `schema_alert.json`.
Meme mouvement au poll suivant = pas de rejeu.
Rejeu si ca s'accelere ou si on passe de 2 a tous.

## CIPHER

F04 n'a pas d'HTML. Il consomme `schema_alert.json`.
Token Telegram : env hote, jamais le git.
