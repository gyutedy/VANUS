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


def _load_fi():
    path = CODEBASE / "footinsights.py"
    spec = importlib.util.spec_from_file_location("footinsights", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def test_tips_become_match_lines_by_competition_today_only():
    fi = _load_fi()
    slates = fi.parse_slates(
        _html("footinsights_today.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://footinsights.com/predictions/",
    )
    names = {s["competition"] for s in slates}
    assert names == {"Premier League", "La Liga"}
    for slate in slates:
        assert slate["index"] == "footinsights"
        assert slate["slate_date"] == "2026-11-07"
        validate_instance(slate, "schema_slate.json")
        homes = [m["home"] for m in slate["matches"]]
        assert "Arsenal" not in homes


def test_collable_tip_has_pick_odds_and_raw_ref():
    fi = _load_fi()
    slate = fi.parse_html(
        _html("footinsights_today.html"),
        competition="Premier League",
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    leeds = next(m for m in slate["matches"] if m["home"] == "Leeds United")
    assert leeds["away"] == "Tottenham"
    assert leeds["kickoff"] == "2026-11-07T12:30:00Z"
    assert leeds["pick"] == "Tottenham win"
    assert leeds["model_pct"] == 0.7
    assert leeds["odds"]["pick"] == 2.59
    assert leeds["raw_ref"] == "leeds-united-vs-tottenham-2026-11-07"


def test_locked_tip_still_a_match_line_pick_null():
    fi = _load_fi()
    slate = fi.parse_html(
        _html("footinsights_today.html"),
        competition="La Liga",
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    malaga = next(m for m in slate["matches"] if m["home"] == "Malaga")
    assert malaga["away"] == "Racing Santander"
    assert malaga["kickoff"] == "2026-11-07T13:00:00Z"
    assert malaga["pick"] is None
    assert malaga["odds"] == {}
    assert malaga["raw_ref"] == "malaga-vs-racing-santander-2026-11-07"


def test_blog_article_is_raw_ref_not_markdown():
    fi = _load_fi()
    html = _html("footinsights_today.html")
    refs = fi.parse_blog_refs(html)
    assert "football-bet-of-the-day" in refs
    assert "double-chance-guide" in refs
    assert "topic" not in refs
    assert all("/" not in r for r in refs)
    assert all(not r.endswith(".md") for r in refs)
    for slate in fi.parse_slates(html, captured_at="2026-11-07T10:00:00Z"):
        blob = json.dumps(slate)
        assert "How our football Bet of the Day is picked" not in blob
        assert "# " not in blob
        for match in slate["matches"]:
            assert "blog/" not in (match.get("raw_ref") or "")


def test_empty_html_is_empty_list_not_crash():
    fi = _load_fi()
    slate = fi.parse_html(
        _html("footinsights_empty.html"),
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["matches"] == []
    assert slate["index"] == "footinsights"
    assert fi.parse_blog_refs(_html("footinsights_empty.html")) == []


def test_user_agent_is_clear_not_browser():
    fi = _load_fi()
    assert fi.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in fi.USER_AGENT
    assert "Mozilla" not in fi.USER_AGENT


def test_run_writes_out_per_index(tmp_path):
    out = tmp_path / "OUT"
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--html",
        str(HTML_DIR / "footinsights_today.html"),
        "--index",
        "footinsights",
        "--out",
        str(out),
        "--source-url",
        "https://footinsights.com/predictions/",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert paths
    names = {p.name for p in paths}
    assert any(n.startswith("slate_footinsights_") for n in names)
    assert not any("predictlix" in n or "metapred" in n or "dailysportpick" in n for n in names)
    for path in paths:
        slate = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(slate, "schema_slate.json")
        assert slate["index"] == "footinsights"
