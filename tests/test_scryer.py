from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F01_SCRYER" / "CODEBASE"


def _load_scryer():
    path = CODEBASE / "scryer.py"
    spec = importlib.util.spec_from_file_location("scryer", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _slate(index: str, competition: str, date: str, matches: list[dict]) -> dict:
    return {
        "contract": "vanus.slate.v1",
        "index": index,
        "competition": competition,
        "slate_date": date,
        "captured_at": "2026-11-07T10:00:00Z",
        "matches": matches,
    }


def _row(home: str, away: str, kickoff: str, **extra) -> dict:
    row = {"home": home, "away": away, "kickoff": kickoff, "score": None, "pick": extra.pop("pick", None)}
    row.update(extra)
    return row


def test_same_clubs_different_spellings_one_match_key():
    sc = _load_scryer()
    slates = [
        _slate(
            "predictlix",
            "La Liga",
            "2026-11-07",
            [_row("Atlético Madrid", "Valencia CF", "2026-11-07T20:00:00Z", pick="1")],
        ),
        _slate(
            "dailysportpick",
            "LaLiga",
            "2026-11-07",
            [_row("Atletico Madrid", "Valencia", "2026-11-07T20:00:00Z", pick="1")],
        ),
    ]
    aliases = {"teams": {}}
    matches = sc.align(slates, aliases)
    assert len(matches) == 1
    match = matches[0]
    validate_instance(match, "schema_match.json")
    assert match["match_key"] == "laliga:2026-11-07:2000:atletico-madrid:valencia"
    assert match["indexes"]["predictlix"] is not None
    assert match["indexes"]["dailysportpick"] is not None
    assert aliases["teams"] == {}


def test_kickoff_too_far_not_fused():
    sc = _load_scryer()
    slates = [
        _slate(
            "predictlix",
            "La Liga",
            "2026-11-07",
            [_row("Athletic Club", "Valencia", "2026-11-07T12:00:00Z")],
        ),
        _slate(
            "dailysportpick",
            "La Liga",
            "2026-11-07",
            [_row("Athletic Club", "Valencia", "2026-11-07T15:00:00Z")],
        ),
    ]
    matches = sc.align(slates, {"teams": {}})
    assert len(matches) == 2
    keys = {m["match_key"] for m in matches}
    assert keys == {
        "laliga:2026-11-07:1200:athletic-club:valencia",
        "laliga:2026-11-07:1500:athletic-club:valencia",
    }
    for match in matches:
        validate_instance(match, "schema_match.json")
        filled = [k for k, v in match["indexes"].items() if v is not None]
        holes = [k for k, v in match["indexes"].items() if v is None]
        assert len(filled) == 1
        assert len(holes) == 1


def test_athletic_vs_athletic_bilbao_is_hole():
    sc = _load_scryer()
    slates = [
        _slate(
            "predictlix",
            "La Liga",
            "2026-11-07",
            [_row("Athletic Club", "Valencia CF", "2026-11-07T20:00:00Z", pick="1")],
        ),
        _slate(
            "dailysportpick",
            "La Liga",
            "2026-11-07",
            [_row("Athletic Bilbao", "Valencia", "2026-11-07T20:00:00Z", pick="X")],
        ),
    ]
    matches = sc.align(slates, {"teams": {}})
    assert len(matches) == 2
    keys = {m["match_key"] for m in matches}
    assert keys == {
        "laliga:2026-11-07:2000:athletic-club:valencia",
        "laliga:2026-11-07:2000:athletic-bilbao:valencia",
    }
    by_home = {m["home"]: m for m in matches}
    club = by_home["Athletic Club"]
    bilbao = by_home["Athletic Bilbao"]
    validate_instance(club, "schema_match.json")
    validate_instance(bilbao, "schema_match.json")
    assert club["indexes"]["predictlix"] is not None
    assert club["indexes"]["dailysportpick"] is None
    assert bilbao["indexes"]["dailysportpick"] is not None
    assert bilbao["indexes"]["predictlix"] is None


def test_kickoff_within_window_fuses():
    sc = _load_scryer()
    slates = [
        _slate(
            "predictlix",
            "La Liga",
            "2026-11-07",
            [_row("FC Barcelona", "Girona", "2026-11-07T20:00:00Z")],
        ),
        _slate(
            "besoccer",
            "La Liga",
            "2026-11-07",
            [_row("Barcelona", "Girona", "2026-11-07T20:30:00Z")],
        ),
    ]
    matches = sc.align(slates, {"teams": {}})
    assert len(matches) == 1
    match = matches[0]
    validate_instance(match, "schema_match.json")
    assert match["match_key"] == "laliga:2026-11-07:2000:barcelona:girona"
    assert match["indexes"]["predictlix"] is not None
    assert match["indexes"]["besoccer"] is not None
    assert sc.WINDOW_MINUTES == 45


def test_aliases_enriched_on_fuzzy():
    sc = _load_scryer()
    slates = [
        _slate(
            "predictlix",
            "La Liga",
            "2026-11-07",
            [_row("Atletico Madrid", "Sevilla", "2026-11-07T18:00:00Z")],
        ),
        _slate(
            "metapred",
            "La Liga",
            "2026-11-07",
            [_row("Atletico de Madrid", "Sevilla", "2026-11-07T18:00:00Z")],
        ),
    ]
    aliases = {"teams": {}}
    matches = sc.align(slates, aliases)
    assert len(matches) == 1
    validate_instance(matches[0], "schema_match.json")
    teams = aliases["teams"]
    assert teams
    flat = set(teams.keys())
    for values in teams.values():
        flat.update(values)
    assert "atletico madrid" in flat
    assert "atletico de madrid" in flat


def test_empty_slates_no_crash():
    sc = _load_scryer()
    slates = [
        _slate("predictlix", "La Liga", "2026-11-07", []),
        _slate("dailysportpick", "La Liga", "2026-11-07", []),
    ]
    matches = sc.align(slates, {"teams": {}})
    assert matches == []


def test_ac_milan_not_merged_with_milan():
    sc = _load_scryer()
    slates = [
        _slate(
            "predictlix",
            "Serie A",
            "2026-11-07",
            [_row("AC Milan", "Roma", "2026-11-07T19:00:00Z")],
        ),
        _slate(
            "dailysportpick",
            "Serie A",
            "2026-11-07",
            [_row("Milan", "Roma", "2026-11-07T19:00:00Z")],
        ),
    ]
    matches = sc.align(slates, {"teams": {}})
    assert len(matches) == 2
    for match in matches:
        validate_instance(match, "schema_match.json")
        holes = [v for v in match["indexes"].values() if v is None]
        assert len(holes) == 1


def test_run_writes_match_files(tmp_path):
    src = tmp_path / "IN"
    out = tmp_path / "OUT"
    aliases = tmp_path / "aliases.json"
    src.mkdir()
    slate = _slate(
        "predictlix",
        "La Liga",
        "2026-11-07",
        [_row("Malaga", "Racing Santander", "2026-11-07T16:00:00Z", pick="X")],
    )
    (src / "slate_predictlix_la_liga_2026-11-07.json").write_text(
        json.dumps(slate, indent=2) + "\n", encoding="utf-8"
    )
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--in",
        str(src),
        "--out",
        str(out),
        "--aliases",
        str(aliases),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert len(paths) == 1
    match = json.loads(paths[0].read_text(encoding="utf-8"))
    validate_instance(match, "schema_match.json")
    assert match["indexes"]["predictlix"]["pick"] == "X"
    saved = json.loads(aliases.read_text(encoding="utf-8"))
    assert saved == {"teams": {}}
