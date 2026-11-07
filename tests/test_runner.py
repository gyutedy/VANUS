from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F00_INFOCYTE" / "CODEBASE"
HTML_DIR = Path(__file__).resolve().parent / "fixtures" / "html"


def _load_runner():
    sys.path.insert(0, str(CODEBASE))
    path = CODEBASE / "runner.py"
    spec = importlib.util.spec_from_file_location("f00_runner", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _html(name: str) -> str:
    return (HTML_DIR / name).read_text(encoding="utf-8")


def _sources() -> dict:
    return json.loads((REPO / "F00_INFOCYTE" / "IN" / "sources.json").read_text(encoding="utf-8"))


def _fixtures() -> dict[str, str]:
    return {
        "predictlix": _html("predictlix_la_liga.html"),
        "dailysportpick": _html("dailysportpick_today.html"),
        "metapred": _html("metapred_today.html"),
        "footinsights": _html("footinsights_today.html"),
        "besoccer": _html("besoccer_today.html"),
    }


def test_runner_fixtures_write_n_slates(tmp_path):
    runner = _load_runner()
    out = tmp_path / "OUT"
    sleeps: list[float] = []
    result = runner.run_fleet(
        _sources(),
        html_by_index=_fixtures(),
        out_dir=out,
        delay=0.5,
        sleep=sleeps.append,
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    paths = list(out.glob("slate_*.json"))
    assert len(paths) >= 5
    assert len(result["written"]) == len(paths)
    indexes = set()
    for path in paths:
        slate = json.loads(path.read_text(encoding="utf-8"))
        validate_instance(slate, "schema_slate.json")
        indexes.add(slate["index"])
    assert indexes == {"predictlix", "dailysportpick", "metapred", "footinsights", "besoccer"}
    assert result["called"] == [
        "predictlix",
        "dailysportpick",
        "metapred",
        "footinsights",
        "besoccer",
    ]
    assert result["skipped"] == []
    assert len(sleeps) == 4
    assert all(s == 0.5 for s in sleeps)


def test_disabled_index_not_called(tmp_path):
    runner = _load_runner()
    sources = _sources()
    for ix in sources["indexes"]:
        if ix["id"] == "besoccer":
            ix["enabled"] = False
    called_fetch: list[str] = []

    def fetch_bs(url):
        called_fetch.append(url)
        return {"ok": True, "status": 200, "skipped": False, "html": "<html></html>", "retries": 0}

    html_map = {k: v for k, v in _fixtures().items() if k != "besoccer"}
    result = runner.run_fleet(
        sources,
        html_by_index=html_map,
        fetchers={"besoccer": fetch_bs},
        out_dir=tmp_path / "OUT",
        delay=0,
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    assert "besoccer" not in result["called"]
    assert called_fetch == []
    names = {p.name for p in (tmp_path / "OUT").glob("slate_*.json")}
    assert not any("besoccer" in n for n in names)


def test_runner_406_skips_besoccer_no_retry(tmp_path):
    runner = _load_runner()
    calls: list[str] = []
    logs: list[str] = []

    def fetch_406(url):
        calls.append(url)
        return {
            "ok": False,
            "status": 406,
            "skipped": True,
            "html": None,
            "url": url,
            "retries": 0,
        }

    html_map = {k: v for k, v in _fixtures().items() if k != "besoccer"}
    result = runner.run_fleet(
        _sources(),
        html_by_index=html_map,
        fetchers={"besoccer": fetch_406},
        out_dir=tmp_path / "OUT",
        delay=0,
        log=logs.append,
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    assert calls == ["https://www.besoccer.com/"]
    assert len(calls) == 1
    skipped = [s for s in result["skipped"] if s["index"] == "besoccer"]
    assert skipped and skipped[0]["status"] == 406
    assert skipped[0]["retries"] == 0
    names = {p.name for p in (tmp_path / "OUT").glob("slate_*.json")}
    assert not any("besoccer" in n for n in names)


def test_runner_fetches_all_enabled_indexes(tmp_path):
    runner = _load_runner()
    called: list[str] = []
    fixtures = _fixtures()

    def make_fetch(index_id: str, html: str):
        def fetch(url):
            called.append(index_id)
            return {
                "ok": True,
                "status": 200,
                "skipped": False,
                "html": html,
                "url": url,
                "retries": 0,
            }

        return fetch

    result = runner.run_fleet(
        _sources(),
        fetchers={k: make_fetch(k, v) for k, v in fixtures.items()},
        out_dir=tmp_path / "OUT",
        delay=0,
        captured_at="2026-11-07T10:00:00Z",
        slate_date="2026-11-07",
    )
    assert result["called"] == [
        "predictlix",
        "dailysportpick",
        "metapred",
        "footinsights",
        "besoccer",
    ]
    assert set(called) == set(result["called"])
    assert called.count("predictlix") == 1
    assert result["skipped"] == []
    assert len(list((tmp_path / "OUT").glob("slate_*.json"))) >= 5


def test_predictlix_whitelist_is_today_hub():
    runner = _load_runner()
    entries = runner.source_entries_for(_sources(), "predictlix")
    urls = [e["url"] for e in entries]
    assert urls == ["https://predictlix.com/predictions/"]


def test_httpget_error_is_skip_no_retry():
    import io
    import urllib.error

    sys.path.insert(0, str(CODEBASE))
    import httpget

    calls = {"n": 0}
    logs: list[str] = []

    def urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(
            "https://predictlix.com/",
            403,
            "Forbidden",
            {},
            io.BytesIO(b""),
        )

    result = httpget.fetch(
        "https://predictlix.com/",
        index="predictlix",
        urlopen=urlopen,
        log=logs.append,
    )
    assert result["skipped"] is True
    assert result["ok"] is False
    assert result["status"] == 403
    assert result["retries"] == 0
    assert result["html"] is None
    assert calls["n"] == 1
    assert any("predictlix" in line and "skip" in line for line in logs)
    assert httpget.USER_AGENT.startswith("VANUS/")
    assert "Chrome" not in httpget.USER_AGENT
