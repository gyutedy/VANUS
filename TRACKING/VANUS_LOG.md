# VANUS_LOG

## 2026-11-07

- Temple ouvert : structure + docs + contrats.
- Aucun code metier.
- Runtime cible : PythonAnywhere.
- Depot public : https://github.com/gyutedy/VANUS
- Pas lie a Perturabo.
- Plan 14 phases : `docs/05_IMPLEMENTATION.md` (une phase = une session).
- PHASE-01 : `VANUS_CUSTOS.py`, pytest, fixtures JSON, 21 tests. Zero parseur.
- PHASE-02 : F00 PredictLix. `predictlix.py` + `run.py`, fixtures HTML, 28 tests. Un site. Pas DSP.
- PHASE-03 : F00 DailySportPick. `dailysportpick.py`, fixtures HTML, 34 tests. OUT separe par index. Pas MetaPred.
- PHASE-04 : F00 MetaPred. `metapred.py`, fixtures HTML, 40 tests. Today only, par competition. Pas FootInsights.
- PHASE-05 : F00 FootInsights. `footinsights.py`, fixtures HTML, 47 tests. Tips → lignes match si collables ; article → `raw_ref` seulement. Pas BeSoccer.
- PHASE-06 : F00 BeSoccer + runner. `besoccer.py` + `runner.py`, fixtures HTML, 56 tests. 406 = skip 0 retry. Indexes `enabled`, delai inter-sites. Pas F01.
- PHASE-07 : F01 SCRYER. `scryer.py` + `run.py`, 64 tests. Cle composite ligue+date+creneau±45 min+noms. Alias auto. Athletic Club ≠ Athletic Bilbao. Pas F02.
- PHASE-08 : F02 snapshots + export. `mnemos.py` + `run.py`. 2 polls → 2 points. Export JSON/CSV relit sans re-fetch. Pas blogs.
- PHASE-09 : F02 blogs. `blogs.py`. 1er run `new` ; identique `unchanged` ; contenu change `updated`. Pas miroir public. Pas F03.
- PHASE-10 : F03 evolution + alertes. `speculum.py` + `run.py`. 3 horodatages → 3 points. 2/3 = alarm. 1/3 = rien. Fingerprint. Pinnacle absent ≠ desaccord. Pas CELL.
- PHASE-11 : F05 CELL menus + popup. `cell.py` + `run.py`. Lit OUT/ARCHIVUM. Popup 1 match, accordéons, tiroir vide = pas trouve. Zero fetch sortant. Pas CIPHER.
- PHASE-12 : F04 CIPHER Telegram. `cipher.py` + `run.py`. API mockee. 2x meme alerte = 1 send. JACKPOT ≠ ALARME. Token absent = log, pas crash. Pas TARIEL.
- PHASE-13 : TARIEL + PA. `tariel.py` + `gates.py`. Horloge fake, 2 ticks → F00 puis F01… OUT. TARIEL sans HTML. `pa_task` une passe. `pa_web` GET `/`. Pas E2E.
- PHASE-14 : E2E flotte + CI. HTML → slates → matchs → snapshots → evolution/alert → CELL HTML + CIPHER mock. Workflow GitHub pytest only. `harness_ready`.
- 14 phases closes. Flotte testable hors PA.
- F00 Vitibet : `vitibet.py` + whitelist GET quicktips today. Un slate par ligue. INDEX + 1/X/2 publics. Pas de spider.
- F05 skin Temple Vanus : plaque Officio/VANUS/CELL, dalles, SVG evolution (polyline). Un poll = point + attente 2e releve. Pas de son. Source git, pas HTML OUT.
- 2026-11-10 : plan SIGNAL (`docs/06_SIGNAL.md`) PHASE-15 a 17. Cahier B coller-tel-quel. Pas de code metier encore. PARI hors scope. Prochaine session = PHASE-15 contrat.
- PHASE-15 : `CONTRACTS/schema_signal.json` + golden `signal.json` + `test_contracts`. Pas `signals_export.py`. Prochaine = PHASE-16.
- PHASE-16 : `signals_export.py` + `tests/test_signal.py`. run.py / TARIEL intacts. Prochaine = PHASE-17.
- PHASE-17 : `--signal-out` F03/TARIEL, E2E `latest.json`, docs PA `/signals/`. SIGNAL 15-17 closes.
