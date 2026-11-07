# PHASE-14

2026-11-07 — E2E flotte + CI pytest.
- `tests/test_e2e.py` : HTML fixtures → F00 slates → F01 matchs → F02 snapshots → F03 evolution/alert → F05 HTML + F04 mock. Token absent = log.
- `.github/workflows/pytest.yml` : pytest only. Pas de schedule. Pas de cron de capture.
- `GUIDE_UTILISATION.md` : commandes reelles. `liber_vanus.json` = `harness_ready`.
