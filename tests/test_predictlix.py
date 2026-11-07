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


def _load_predictlix():
    path = CODEBASE / "predictlix.py"
    spec = importlib.util.spec_from_file_location("predictlix", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def test_fixture_yields_valid_slate():
    plx = _load_predictlix()
    slate = plx.parse_html(
        _html("predictlix_la_liga.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://predictlix.com/predictions/spain/la-liga/",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["index"] == "predictlix"
    assert slate["contract"] == "vanus.slate.v1"
    assert slate["competition"] == "La Liga"
    assert slate["slate_date"] == "2026-11-07"
    assert len(slate["matches"]) == 3


def test_unit_is_match_not_market():
    plx = _load_predictlix()
    slate = plx.parse_html(_html("predictlix_la_liga.html"), captured_at="2026-11-07T10:00:00Z")
    first = slate["matches"][0]
    assert first["home"] == "Malaga"
    assert first["away"] == "Racing Santander"
    assert first["kickoff"] == "2026-11-07T16:00:00Z"
    assert first["pick"] == "X"
    assert first["model_pct"] == 0.284
    assert first["score"] is None
    assert first["odds"]["1x2"]["draw"] == 3.72
    assert "ev" in first["odds"]
    assert first["raw_ref"] == "malaga-vs-racing-santander"


def test_markets_are_fields_pinnacle_only_if_on_page():
    plx = _load_predictlix()
    slate = plx.parse_html(_html("predictlix_la_liga.html"), captured_at="2026-11-07T10:00:00Z")
    athletic = next(m for m in slate["matches"] if m["home"] == "Athletic Club")
    assert athletic["away"] == "Valencia"
    assert athletic["pick"] == "1"
    assert athletic["model_pct"] == 0.42
    assert athletic["odds"]["1x2"]["home"] == 1.85
    assert athletic["odds"]["pinnacle"]["price"] == 1.85
    malaga = slate["matches"][0]
    assert "pinnacle" not in malaga["odds"]


def test_finished_match_keeps_score_null_pick_ok():
    plx = _load_predictlix()
    slate = plx.parse_html(_html("predictlix_la_liga.html"), captured_at="2026-11-07T10:00:00Z")
    girona = next(m for m in slate["matches"] if m["home"] == "Girona")
    assert girona["away"] == "Sevilla"
    assert girona["score"] == "2-1"
    assert girona["pick"] is None
    assert girona["model_pct"] is None
    assert girona["odds"] == {}


def test_empty_html_is_empty_list_not_crash():
    plx = _load_predictlix()
    slate = plx.parse_html(_html("predictlix_empty.html"), captured_at="2026-11-07T10:00:00Z")
    validate_instance(slate, "schema_slate.json")
    assert slate["matches"] == []


def test_parse_slates_splits_leagues():
    plx = _load_predictlix()
    slates = plx.parse_slates(
        _html("predictlix_today_hub.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://predictlix.com/predictions/",
    )
    names = [s["competition"] for s in slates]
    assert names == ["England Premier League", "England Championship"]
    for slate in slates:
        validate_instance(slate, "schema_slate.json")
        assert slate["index"] == "predictlix"
    pl = next(s for s in slates if "Premier League" in s["competition"])
    assert pl["matches"][0]["home"] == "Fulham"
    ch = next(s for s in slates if "Championship" in s["competition"])
    assert ch["matches"][0]["home"] == "Birmingham"
    assert ch["matches"][0]["odds"]["pinnacle"]["price"] == 1.88


def test_user_agent_is_clear_not_browser():
    plx = _load_predictlix()
    assert plx.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in plx.USER_AGENT
    assert "Mozilla" not in plx.USER_AGENT


def test_run_writes_out(tmp_path):
    out = tmp_path / "OUT"
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--html",
        str(HTML_DIR / "predictlix_la_liga.html"),
        "--out",
        str(out),
        "--source-url",
        "https://predictlix.com/predictions/spain/la-liga/",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    written = Path(proc.stdout.strip())
    assert written.is_file()
    slate = json.loads(written.read_text(encoding="utf-8"))
    validate_instance(slate, "schema_slate.json")
    assert slate["index"] == "predictlix"
    assert len(slate["matches"]) == 3
