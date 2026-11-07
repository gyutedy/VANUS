# Whitelist sources

Lecture de pages **publiques** seulement. Liste fermee. Pas de spider.

| Index | Intention | Note |
|---|---|---|
| PredictLix | slate du jour par competition | HTML serveur. PHASE-02 : fixture `tests/fixtures/html/predictlix_la_liga.html` (La Liga). Chemin whitelist : `/predictions/spain/la-liga/`. |
| DailySportPick | pronos du jour | HTML serveur. PHASE-03 : fixture `tests/fixtures/html/dailysportpick_today.html`. Chemin whitelist : `https://dailysportpick.com/fr/`. Ligues vues : La Liga, Premier League, Serie A. |
| MetaPred | matchs du jour | HTML serveur |
| FootInsights | blog + tips | HTML serveur |
| BeSoccer | cotes / live si GET honnete | 406 = skip, pas de deguisement |

AlternativeTo : hors perimetre.

Pinnacle : **pas une source**. Champ seulement si deja present dans une page d'index.

Respect : User-Agent clair, delai inter-sites, robots.txt.
