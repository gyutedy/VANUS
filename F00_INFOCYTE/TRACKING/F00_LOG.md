# F00 INFOCYTE

2026-11-07 — silo cree. CODEBASE vide. Aucun parseur.

2026-11-07 — PHASE-02 PredictLix.
- `CODEBASE/predictlix.py` : parse HTML public (fixture locale) → `vanus.slate.v1`.
- `CODEBASE/run.py` : IN HTML fichier → OUT JSON. Pas de GET reseau dans cette phase.
- Unite = match (home/away/kickoff). Marches = champs (`odds.1x2`, `ev`, `pinnacle` si deja dans la page).
- UA clair : `VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)`.
- Ligues vues dans la fixture : La Liga (`/predictions/spain/la-liga/`).
- Pas DSP, pas MetaPred, pas runner multi-index.

2026-11-07 — PHASE-03 DailySportPick.
- `CODEBASE/dailysportpick.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par competition.
- `run.py` : `--index dailysportpick` ecrit `slate_dailysportpick_<comp>_<date>.json`.
- Unite = match. Pick/cotes absents → `null` / `{}`. Extra cards inclus.
- Ligues vues dans la fixture : La Liga, Premier League, Serie A. Chemin whitelist : `https://dailysportpick.com/fr/`.
- Pas MetaPred, pas FootInsights, pas runner multi-index.

2026-11-07 — PHASE-04 MetaPred.
- `CODEBASE/metapred.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par competition.
- Today only : slug `DD-MM-YYYY` hors `slate_date` ignore. Blocs Demain/Hier ignores.
- Ligues vues dans la fixture : Premier League, La Liga. Chemin whitelist : `https://metapred.com/fr/pronostic/aujourd-hui`.
- Pas FootInsights, pas BeSoccer, pas runner multi-index.

2026-11-07 — PHASE-05 FootInsights.
- `CODEBASE/footinsights.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par competition.
- Tips collables (home/away/kickoff) → lignes match. Tip locked → pick/odds nuls, match conserve.
- Articles blog → `parse_blog_refs` slugs seulement. Pas de copie markdown (F02).
- Ligues vues dans la fixture : Premier League, La Liga. Chemin whitelist : `https://footinsights.com/predictions/`.
- Pas BeSoccer, pas runner multi-index.

2026-11-07 — PHASE-06 BeSoccer + runner.
- `CODEBASE/besoccer.py` : parse HTML public (fixture locale) → `vanus.slate.v1`. GET honnete, UA clair. 406 = skip + log, 0 retry, pas de deguisement.
- `CODEBASE/runner.py` : indexes `enabled` dans `IN/sources.json`, delai inter-sites, OUT un slate par index x competition.
- Ligues vues dans la fixture : Premier League, La Liga. Chemin whitelist : `https://www.besoccer.com/`.
- Index disabled = pas d'appel. Pas F01.

2026-11-07 — GET honnete pour tous les indexes enabled.
- `CODEBASE/httpget.py` : GET UA VANUS, 0 retry, skip HTTPError/URLError.
- `runner.py` : plus de `no_fetcher`. PredictLix, DSP, MetaPred, FootInsights, BeSoccer GET la whitelist.
- 406 BeSoccer inchange. Pas de deguisement.

2026-11-07 — PredictLix hub today.
- Un GET `https://predictlix.com/predictions/`. `parse_slates` decoupe par h2 ligue.
- Pas 140 GET. Pas de spider. Whitelist = cette URL.

2026-11-07 — FootInsights toutes dates + tips publics.
- `parse_slates` lit chaque `section#day-YYYY-MM-DD` de `/predictions/`.
- JSON `data-unlock` deja dans le HTML public → pick/cote. Pas de login. Locked sans JSON = pick null.

2026-11-07 — Vitibet index F00.
- `CODEBASE/vitibet.py` : parse HTML public (fixture locale) → `vanus.slate.v1`, un slate par ligue.
- Un GET `https://www.vitibet.com/index.php?clanek=quicktips&sekce=fotbal&lang=fr`. Page unique today. Pas de spider.
- Unite = match. Tip `1`/`X`/`2`/`1X`… + `model_pct` depuis les % publics. INDEX Vitibet → `odds.index`. Score FT si present.
- Ligues vues dans la fixture : Angleterre Premier League, Championship.
