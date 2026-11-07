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


def test_tips_become_match_lines_by_competition_all_dates():
    fi = _load_fi()
    slates = fi.parse_slates(
        _html("footinsights_today.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://footinsights.com/predictions/",
    )
    names = {s["competition"] for s in slates}
    assert names == {"Premier League", "La Liga"}
    dates = {s["slate_date"] for s in slates}
    assert dates == {"2026-11-07", "2026-11-08"}
    for slate in slates:
        assert slate["index"] == "footinsights"
        validate_instance(slate, "schema_slate.json")
    today_pl = next(
        s for s in slates if s["competition"] == "Premier League" and s["slate_date"] == "2026-11-07"
    )
    assert "Arsenal" not in [m["home"] for m in today_pl["matches"]]
    tomorrow = next(s for s in slates if s["slate_date"] == "2026-11-08")
    assert any(m["home"] == "Arsenal" for m in tomorrow["matches"])


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


def test_unlock_json_on_page_fills_locked_tip():
    fi = _load_fi()
    html = """
    <section id="day-2026-11-07" class="day">
    <section data-league="premier-league" class="pgroup">
    <h3 class="n">Premier League</h3>
    <a href="/predictions/arsenal-vs-hull-city-2026-11-07/" class="prow is-locked" data-day="2026-11-07" data-home="Arsenal" data-away="Hull City">
    <span class="sr-only">Tip and odds locked</span>
    <script type="application/json" data-unlock>{"m":91,"t":[["best","1x2","home",0.8579,1.17,0,null]],"p":[0.8579,0.1054,0.0367]}</script>
    <time datetime="2026-11-07T15:00:00+00:00">15:00</time>
    <span class="xt-call locked-call">Locked tip</span>
    </a>
    </section>
    </section>
    """
    slate = fi.parse_html(html, competition="Premier League", captured_at="2026-11-07T10:00:00Z")
    validate_instance(slate, "schema_slate.json")
    row = slate["matches"][0]
    assert row["home"] == "Arsenal"
    assert row["away"] == "Hull City"
    assert row["pick"] == "1"
    assert row["model_pct"] == 0.8579
    assert row["odds"]["pick"] == 1.17
    assert row["odds"]["1x2"]["home"] == 1.17


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
