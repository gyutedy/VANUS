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


def _load():
    path = CODEBASE / "vitibet.py"
    spec = importlib.util.spec_from_file_location("vitibet", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def test_slates_by_competition():
    vb = _load()
    slates = vb.parse_slates(
        _html("vitibet_today.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://www.vitibet.com/index.php?clanek=quicktips&sekce=fotbal&lang=fr",
    )
    names = {s["competition"] for s in slates}
    assert names == {"Angleterre: Premier League", "Angleterre: Championship"}
    for slate in slates:
        assert slate["index"] == "vitibet"
        assert slate["slate_date"] == "2026-11-07"
        validate_instance(slate, "schema_slate.json")


def test_unit_is_match_with_pick_and_index():
    vb = _load()
    slate = vb.parse_html(
        _html("vitibet_today.html"),
        competition="Angleterre: Premier League",
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    fulham = next(m for m in slate["matches"] if m["home"] == "Fulham")
    assert fulham["away"] == "Newcastle"
    assert fulham["kickoff"] == "2026-11-07T15:00:00Z"
    assert fulham["pick"] == "1"
    assert fulham["model_pct"] == 0.47
    assert fulham["odds"]["index"] == 0.40
    assert fulham["score"] is None
    leeds = next(m for m in slate["matches"] if m["home"] == "Leeds")
    assert leeds["score"] == "1-0"
    assert leeds["pick"] == "1X"
    assert leeds["model_pct"] == 0.70


def test_empty_html_is_empty_list_not_crash():
    vb = _load()
    slate = vb.parse_html(
        _html("vitibet_empty.html"),
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["matches"] == []
    assert slate["index"] == "vitibet"


def test_user_agent_is_clear_not_browser():
    vb = _load()
    assert vb.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in vb.USER_AGENT
    assert "Mozilla" not in vb.USER_AGENT


def test_run_writes_out_per_index(tmp_path):
    out = tmp_path / "OUT"
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--html",
        str(HTML_DIR / "vitibet_today.html"),
        "--index",
        "vitibet",
        "--out",
        str(out),
        "--source-url",
        "https://www.vitibet.com/index.php?clanek=quicktips&sekce=fotbal&lang=fr",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert paths
    names = {p.name for p in paths}
    assert any(n.startswith("slate_vitibet_") for n in names)
    assert not any("predictlix" in n or "footinsights" in n for n in names)
    for path in paths:
        slate = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(slate, "schema_slate.json")
        assert slate["index"] == "vitibet"
