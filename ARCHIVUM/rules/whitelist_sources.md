# Whitelist sources

Lecture de pages **publiques** seulement. Liste fermee. Pas de spider.

| Index | Intention | Note |
|---|---|---|
| PredictLix | slate du jour par competition | HTML serveur. PHASE-02 : fixture `tests/fixtures/html/predictlix_la_liga.html` (La Liga). Chemin whitelist : `/predictions/spain/la-liga/`. |
| DailySportPick | pronos du jour | HTML serveur. PHASE-03 : fixture `tests/fixtures/html/dailysportpick_today.html`. Chemin whitelist : `https://dailysportpick.com/fr/`. Ligues vues : La Liga, Premier League, Serie A. |
| MetaPred | matchs du jour | HTML serveur. PHASE-04 : fixture `tests/fixtures/html/metapred_today.html`. Chemin whitelist : `https://metapred.com/fr/pronostic/aujourd-hui`. Ligues vues : Premier League, La Liga. Today only. |
| FootInsights | blog + tips | HTML serveur. PHASE-05 : fixture `tests/fixtures/html/footinsights_today.html`. Chemin whitelist : `https://footinsights.com/predictions/`. Ligues vues : Premier League, La Liga. Tips → lignes match. Article → `raw_ref` seulement (copie markdown = F02). |
| BeSoccer | cotes / live si GET honnete | 406 = skip, pas de deguisement |

AlternativeTo : hors perimetre.

Pinnacle : **pas une source**. Champ seulement si deja present dans une page d'index.

Respect : User-Agent clair, delai inter-sites, robots.txt.
