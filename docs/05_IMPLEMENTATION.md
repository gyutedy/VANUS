# 05 — Plan d'implementation (14 phases)

Source de verite pour les sessions courtes. Une phase = une session.

Lire aussi : `CONTINUATION.md`, `VERBUM.md`, `HERESIE.md`, `TODO.md`.

---

## Regle d'une phase

1. Lire `CONTINUATION.md` + ce fichier + la phase courante.
2. Coder **uniquement** cette phase. Pas la suivante.
3. Tests `pytest` : fixtures locales, **pas de reseau** (live HTTP = `@pytest.mark.live`, skip par defaut).
4. Maj `CONTINUATION.md`, `TODO.md`, `TRACKING/VANUS_LOG.md`, log de la fregate.
5. Commit + push. Message : `phase-NN: …`
6. **STOP.** Interdit d'enchainer.

## Isolation

- Chaque fregate = `CODEBASE/run.py` (IN → OUT).
- TARIEL = `subprocess`, jamais `from F00… import`.
- Tests d'integration copient des JSON. Ils n'importent pas deux CODEBASE dans le meme module metier.
- Zero appel direct entre fregates.

## Heresies (rappel)

Pas d'import croise F00↔F05, pas de scrape Pinnacle, pas de deguisement, 406 = skip, CELL ne calcule pas, TARIEL ne parse pas, pas de secret dans git, pas de cron GitHub de capture.

## Hors phases (ne jamais glisser)

Scrape Pinnacle · cron GH de capture · ecran alias · import Perturabo · tip → `p` · CELL qui recalcule · TARIEL qui parse · secret dans git.

## Ordre fige

`01 → 02 → … → 14`. Pas de CELL avant F03. Pas de CIPHER avant alertes. Pas de PA avant TARIEL.

---

## PHASE-01 — Harness (S)

**Code :** `pytest` + `conftest.py` ; validateur JSON Schema ; `VANUS_CUSTOS.py` (seul a toucher `liber_vanus.json`) ; `tests/fixtures/` (HTML/JSON golden) ; `requirements_test.txt`.

**Tests :** schemas v1 valides ; custos round-trip ; `liber_vanus.json` lisible.

**Docs :** ce fichier ; CONTINUATION = PHASE-01 done.

**Exit :** `pytest` vert, zero parseur.

## PHASE-02 — F00 PredictLix (S)

**Code :** `F00_INFOCYTE/CODEBASE/predictlix.py` + `run.py` (un index). Fixture HTML publique committee. OUT = `schema_slate.json`. UA clair, pas de retry deguise.

**Tests :** fixture → slate valide ; unite = match (home/away/kickoff) ; marches = champs ; 0 match = liste vide pas crash.

**Docs :** F00_LOG + whitelist ligues vues dans la fixture (pas d'URL hors liste).

**Exit :** un seul site. Pas DSP.

## PHASE-03 — F00 DailySportPick (S)

Meme patron que 02. OUT separe par `index`.

**Tests :** noms/horaires parses ; pick/cotes si presents sinon `null`.

## PHASE-04 — F00 MetaPred (S)

Idem.

**Tests :** slate du jour par competition ; pas de page hors today.

## PHASE-05 — F00 FootInsights (S)

Tips + liens blog (copie blog = F02).

**Tests :** tips → lignes match si collables ; article → `raw_ref` seulement, pas le markdown.

## PHASE-06 — F00 BeSoccer + runner (S)

GET honnete ; **406 → skip + log, 0 retry**. Runner F00 : indexes `enabled`, delai inter-sites, `competitions` dans `IN/sources.json`.

**Tests :** 406 mocke = skip ; runner fixtures → N slates dans OUT ; index disabled = pas d'appel.

## PHASE-07 — F01 SCRYER (M)

Cle : competition (pays+ligue canon) + date + creneau ±45 min + home/away + nom normalise. Prefixes pays (England / Angleterre) et ligues nues (Premier League → england). Minuit = heure absente, colle le jour. `aliases.json` enrichi si collage OK. Fuzzy / tokens (Leeds United) seulement si ligue+horaire collent, seuil haut. Echec = `indexes.<id> = null`.

**Tests :** memes clubs orthographes differentes → 1 `match_key` ; horaire trop loin → pas fusion ; Athletic vs Athletic Bilbao sans preuve → tiroir vide.

## PHASE-08 — F02 snapshots + export (S)

Snapshot match × source × marche × `captured_at`. Export JSON/CSV `ARCHIVUM/exports/`.

**Tests :** 2 polls → 2 points ; export relit sans re-fetch.

## PHASE-09 — F02 blogs (S)

Copie locale + hash + `schema_blog.json`. Pas un miroir public.

**Tests :** 1er run `new` ; 2e identique `unchanged` ; contenu change `updated`.

## PHASE-10 — F03 evolution + alertes (M)

Timeline une vue N lignes ; Pinnacle = `pinnacle_ref` **si deja dans un slate**. 2 sources meme sens = `alarm` ; toutes trouvees = `jackpot` ; absent ≠ vote ; `fingerprint` ; re-emission seulement si acceleration ou 2→tous.

**Tests :** 3 horodatages → 3 points ; 2/3 alignes = alarm pas jackpot ; 1/3 = pas d'alerte ; meme fingerprint = pas de 2e alerte ; Pinnacle absent ≠ desaccord.

## PHASE-11 — F05 CELL menus + popup (M)

Lit **seulement** OUT/ARCHIVUM. Menus index → competition → matchs. Popup = 1 match, accordéons (un ouvert), marche defaut 1X2, tiroir evolution, tiroir vide = « pas trouve ».

**Tests :** client HTTP fixture OUT → HTML ; popup d'un `match_key` ; pas de fetch HTTP sortant depuis CELL.

## PHASE-12 — F04 CIPHER (S)

Consomme `schema_alert.json`. Telegram env hote, jamais git. Idempotence fingerprint.

**Tests :** API Telegram mockee ; 2× meme alerte = 1 send ; jackpot ≠ alarm ; token absent = log, pas crash.

## PHASE-13 — TARIEL + PA (M)

TARIEL : poll `poll_minutes` (defaut 120, plancher 30), jusqu'au KO. Portes lecture / alerte. `PA/pa_task.py` = un reveil TARIEL. `PA/pa_web.py` = WSGI → F05 seulement.

**Tests :** horloge fake, 2 ticks → F00 puis F01… fichiers OUT ; TARIEL sans parser HTML ; `pa_task` une passe ; `pa_web` GET `/`.

## PHASE-14 — E2E flotte + CI tests (S)

Pipeline fixtures : HTML → slates → matchs → snapshots → evolution/alert → CELL HTML + CIPHER mock. Workflow GitHub **pytest only** (pas de cron de capture).

**Docs :** GUIDE_UTILISATION commandes reelles ; `liber_vanus.json` status `harness_ready` ; CONTINUATION = code autorise, flotte testable hors PA.

**Exit :** `pytest` vert hors reseau ; greffe = `CONTRACTS/` + `F03_SPECULUM/OUT/`.
