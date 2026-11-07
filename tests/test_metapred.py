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


def _load_mp():
    path = CODEBASE / "metapred.py"
    spec = importlib.util.spec_from_file_location("metapred", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def test_slates_by_competition_today_only():
    mp = _load_mp()
    slates = mp.parse_slates(
        _html("metapred_today.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://metapred.com/fr/pronostic/aujourd-hui",
    )
    names = {s["competition"] for s in slates}
    assert names == {"Premier League", "La Liga"}
    for slate in slates:
        assert slate["index"] == "metapred"
        assert slate["slate_date"] == "2026-11-07"
        validate_instance(slate, "schema_slate.json")
        homes = [m["home"] for m in slate["matches"]]
        assert "Arsenal" not in homes


def test_unit_is_match_with_odds_fields():
    mp = _load_mp()
    slate = mp.parse_html(
        _html("metapred_today.html"),
        competition="Premier League",
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    leeds = next(m for m in slate["matches"] if m["home"] == "Leeds United")
    assert leeds["away"] == "Tottenham"
    assert leeds["kickoff"] == "2026-11-07T12:30:00Z"
    assert leeds["score"] == "0-1"
    assert leeds["odds"]["1x2"]["home"] == 2.73
    assert leeds["odds"]["1x2"]["draw"] == 3.31
    assert leeds["odds"]["1x2"]["away"] == 2.59
    assert leeds["pick"] == "2"
    assert leeds["model_pct"] == 0.36
    assert leeds["raw_ref"] == "leeds-united-vs-tottenham-07-11-2026"


def test_skips_off_today_slug():
    mp = _load_mp()
    slate = mp.parse_html(
        _html("metapred_today.html"),
        competition="Premier League",
        captured_at="2026-11-07T10:00:00Z",
    )
    assert all("08-11-2026" not in (m["raw_ref"] or "") for m in slate["matches"])
    assert all(m["kickoff"].startswith("2026-11-07") for m in slate["matches"])


def test_empty_html_is_empty_list_not_crash():
    mp = _load_mp()
    slate = mp.parse_html(
        _html("metapred_empty.html"),
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["matches"] == []
    assert slate["index"] == "metapred"


def test_user_agent_is_clear_not_browser():
    mp = _load_mp()
    assert mp.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in mp.USER_AGENT
    assert "Mozilla" not in mp.USER_AGENT


def test_run_writes_out_per_index(tmp_path):
    out = tmp_path / "OUT"
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--html",
        str(HTML_DIR / "metapred_today.html"),
        "--index",
        "metapred",
        "--out",
        str(out),
        "--source-url",
        "https://metapred.com/fr/pronostic/aujourd-hui",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert paths
    names = {p.name for p in paths}
    assert any(n.startswith("slate_metapred_") for n in names)
    assert not any("predictlix" in n or "dailysportpick" in n for n in names)
    for path in paths:
        slate = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(slate, "schema_slate.json")
        assert slate["index"] == "metapred"
