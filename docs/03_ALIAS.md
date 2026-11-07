# 03 — Alias (SCRYER)

Pas d'ecran manuel. Auto ou trou.

## Cle composite (pas un nom)

competition (slug canon pays+ligue) + date + creneau (±45 min) + domicile/exterieur + noms normalises.

`Angleterre: Premier League`, `England Premier League` et `Premier League` (sans pays) = `englandpremierleague`. `Ghana Premier League` reste `ghanapremierleague`. Kickoff `T00:00:00Z` (heure absente) colle le meme jour ; un horaire reel remplace minuit sur la fiche.

## Noms

1. Normaliser : minuscules, sans accents, sans FC/CF/AFC, sans ponctuation.
2. `ARCHIVUM/aliases.json` enrichi quand un collagage reussit.
3. Fuzzy seulement si ligue + horaire collent deja, seuil haut.

## Echec

Le tiroir de l'index existe. Il affiche "pas trouve". On n'invente pas.

Mieux vaut 2 sources sures + 1 orphelin qu'une fusion fausse : un mauvais alias pourrit les courbes.
