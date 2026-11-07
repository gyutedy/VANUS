from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F00_INFOCYTE" / "CODEBASE"
HTML_DIR = Path(__file__).resolve().parent / "fixtures" / "html"


def _load_bs():
    path = CODEBASE / "besoccer.py"
    spec = importlib.util.spec_from_file_location("besoccer", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def test_slates_by_competition_today_only():
    bs = _load_bs()
    slates = bs.parse_slates(
        _html("besoccer_today.html"),
        captured_at="2026-11-07T10:00:00Z",
        source_url="https://www.besoccer.com/",
    )
    names = {s["competition"] for s in slates}
    assert names == {"Premier League", "La Liga"}
    for slate in slates:
        assert slate["index"] == "besoccer"
        assert slate["slate_date"] == "2026-11-07"
        validate_instance(slate, "schema_slate.json")
        homes = [m["home"] for m in slate["matches"]]
        assert "Arsenal" not in homes


def test_unit_is_match_with_odds_fields():
    bs = _load_bs()
    slate = bs.parse_html(
        _html("besoccer_today.html"),
        competition="Premier League",
        captured_at="2026-11-07T10:00:00Z",
    )
    validate_instance(slate, "schema_slate.json")
    leeds = next(m for m in slate["matches"] if m["home"] == "Leeds United")
    assert leeds["away"] == "Tottenham"
    assert leeds["kickoff"] == "2026-11-07T12:30:00Z"
    assert leeds["score"] == "0-1"
    assert leeds["odds"]["1x2"]["home"] == 2.70
    assert leeds["odds"]["1x2"]["away"] == 2.55
    assert leeds["pick"] is None
    assert leeds["raw_ref"] == "leeds-united-tottenham-2026-11-07"


def test_empty_html_is_empty_list_not_crash():
    bs = _load_bs()
    slate = bs.parse_html(
        _html("besoccer_empty.html"),
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    validate_instance(slate, "schema_slate.json")
    assert slate["matches"] == []
    assert slate["index"] == "besoccer"


def test_user_agent_is_clear_not_browser():
    bs = _load_bs()
    assert bs.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in bs.USER_AGENT
    assert "Mozilla" not in bs.USER_AGENT


def test_406_mocked_is_skip_no_retry():
    bs = _load_bs()
    calls = {"n": 0}
    logs: list[str] = []

    def urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(
            "https://www.besoccer.com/",
            406,
            "Not Acceptable",
            {},
            io.BytesIO(b""),
        )

    result = bs.fetch(
        "https://www.besoccer.com/",
        urlopen=urlopen,
        log=logs.append,
    )
    assert result["skipped"] is True
    assert result["ok"] is False
    assert result["status"] == 406
    assert result["retries"] == 0
    assert result["html"] is None
    assert calls["n"] == 1
    assert any("406" in line and "skip" in line for line in logs)


def test_run_writes_out_per_index(tmp_path):
    out = tmp_path / "OUT"
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--html",
        str(HTML_DIR / "besoccer_today.html"),
        "--index",
        "besoccer",
        "--out",
        str(out),
        "--source-url",
        "https://www.besoccer.com/",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert paths
    names = {p.name for p in paths}
    assert any(n.startswith("slate_besoccer_") for n in names)
    assert not any("predictlix" in n or "footinsights" in n for n in names)
    for path in paths:
        slate = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(slate, "schema_slate.json")
        assert slate["index"] == "besoccer"
