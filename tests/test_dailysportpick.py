from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F00_INFOCYTE" / "CODEBASE"
HTML_DIR = Path(__file__).resolve().parent / "fixtures" / "html"


def _load_dsp():
    path = CODEBASE / "dailysportpick.py"
    spec = importlib.util.spec_from_file_location("dailysportpick", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def test_fixture_yields_valid_slate_per_competition():
    dsp = _load_dsp()
    slates = dsp.parse_slates(
        _html("dailysportpick_today.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://dailysportpick.com/fr/",
    )
    assert {s["competition"] for s in slates} == {"La Liga", "Premier League", "Serie A"}
    for slate in slates:
        assert slate["index"] == "dailysportpick"
        validate_instance(slate, "schema_slate.json")


def test_names_and_kickoff_parsed():
    dsp = _load_dsp()
    slate = dsp.parse_html(
        _html("dailysportpick_today.html"),
        competition="La Liga",
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["index"] == "dailysportpick"
    assert slate["competition"] == "La Liga"
    assert slate["slate_date"] == "2026-11-07"
    first = next(m for m in slate["matches"] if m["home"] == "Osasuna")
    assert first["away"] == "Athletic Club"
    assert first["kickoff"] == "2026-11-07T17:30:00Z"
    assert first["pick"] == "Osasuna Asian Handicap +1.25"
    assert first["model_pct"] == 0.7326
    assert first["odds"]["pick"] == 1.30
    assert first["raw_ref"] == "osasuna-vs-athletic-club-prediction-2026-11-07"


def test_missing_pick_and_odds_are_null():
    dsp = _load_dsp()
    slate = dsp.parse_html(
        _html("dailysportpick_today.html"),
        competition="La Liga",
        captured_at="2026-11-07T10:00:00Z",
    )
    malaga = next(m for m in slate["matches"] if m["home"] == "Malaga")
    assert malaga["away"] == "Racing Santander"
    assert malaga["kickoff"] == "2026-11-07T13:00:00Z"
    assert malaga["pick"] is None
    assert malaga["model_pct"] is None
    assert malaga["odds"] == {}


def test_empty_html_is_empty_list_not_crash():
    dsp = _load_dsp()
    slate = dsp.parse_html(
        _html("dailysportpick_empty.html"),
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["matches"] == []
    assert slate["index"] == "dailysportpick"


def test_user_agent_is_clear_not_browser():
    dsp = _load_dsp()
    assert dsp.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in dsp.USER_AGENT
    assert "Mozilla" not in dsp.USER_AGENT


def test_out_filename_separated_by_index(tmp_path):
    out = tmp_path / "OUT"
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--html",
        str(HTML_DIR / "dailysportpick_today.html"),
        "--index",
        "dailysportpick",
        "--out",
        str(out),
        "--source-url",
        "https://dailysportpick.com/fr/",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert paths
    names = {p.name for p in paths}
    assert any(n.startswith("slate_dailysportpick_") for n in names)
    assert not any("predictlix" in n for n in names)
    for path in paths:
        slate = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(slate, "schema_slate.json")
        assert slate["index"] == "dailysportpick"
