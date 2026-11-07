from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F02_MNEMOS" / "CODEBASE"


def _load_mnemos():
    path = CODEBASE / "mnemos.py"
    spec = importlib.util.spec_from_file_location("mnemos", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _match(odds_home: float, pick: str = "1") -> dict:
    row = {
        "home": "Athletic Club",
        "away": "Valencia",
        "kickoff": "2026-11-07T20:00:00Z",
        "score": None,
        "pick": pick,
        "odds": {"1x2": {"home": odds_home, "draw": 3.4, "away": 4.2}},
    }
    return {
        "contract": "vanus.match.v1",
        "match_key": "laliga:2026-11-07:2000:athletic-club:valencia",
        "competition": "LaLiga",
        "slate_date": "2026-11-07",
        "home": "Athletic Club",
        "away": "Valencia",
        "kickoff": "2026-11-07T20:00:00Z",
        "score": None,
        "indexes": {
            "predictlix": dict(row),
            "dailysportpick": None,
        },
    }


def test_two_polls_two_points(tmp_path):
    mn = _load_mnemos()
    store = tmp_path / "snapshots"
    mn.ingest([_match(1.85)], "2026-11-07T10:00:00Z", store)
    mn.ingest([_match(1.70)], "2026-11-07T12:00:00Z", store)
    snaps = mn.load_snapshots(store)
    assert len(snaps) == 1
    points = snaps[0]["points"]
    assert len(points) == 2
    assert points[0]["captured_at"] == "2026-11-07T10:00:00Z"
    assert points[0]["odds"]["1x2"]["home"] == 1.85
    assert points[1]["captured_at"] == "2026-11-07T12:00:00Z"
    assert points[1]["odds"]["1x2"]["home"] == 1.70
    assert {p["index"] for p in points} == {"predictlix"}


def test_export_rereads_without_refetch(tmp_path):
    mn = _load_mnemos()
    store = tmp_path / "snapshots"
    exports = tmp_path / "exports"
    mn.ingest([_match(1.85)], "2026-11-07T10:00:00Z", store)
    mn.ingest([_match(1.70)], "2026-11-07T12:00:00Z", store)
    json_path = mn.export_json(store, exports / "snapshots.json", exported_at="2026-11-07T12:05:00Z")
    csv_path = mn.export_csv(store, exports / "snapshots.csv")
    bundle = mn.load_export_json(json_path)
    assert bundle["exported_at"] == "2026-11-07T12:05:00Z"
    assert len(bundle["snapshots"]) == 1
    assert len(bundle["snapshots"][0]["points"]) == 2
    rows = mn.load_export_csv(csv_path)
    homes = [r for r in rows if r["market"] == "1x2" and r["selection"] == "home"]
    assert len(homes) == 2
    assert {r["odds"] for r in homes} == {"1.85", "1.7"}
    assert {r["captured_at"] for r in homes} == {"2026-11-07T10:00:00Z", "2026-11-07T12:00:00Z"}
    assert all(r["index"] == "predictlix" for r in homes)


def test_null_index_is_not_a_point(tmp_path):
    mn = _load_mnemos()
    store = tmp_path / "snapshots"
    mn.ingest([_match(1.85)], "2026-11-07T10:00:00Z", store)
    snap = mn.load_snapshots(store)[0]
    indexes = {p["index"] for p in snap["points"]}
    assert "dailysportpick" not in indexes
    assert "predictlix" in indexes


def test_same_poll_replaces_point(tmp_path):
    mn = _load_mnemos()
    store = tmp_path / "snapshots"
    mn.ingest([_match(1.85)], "2026-11-07T10:00:00Z", store)
    mn.ingest([_match(1.90)], "2026-11-07T10:00:00Z", store)
    points = mn.load_snapshots(store)[0]["points"]
    assert len(points) == 1
    assert points[0]["odds"]["1x2"]["home"] == 1.90


def test_empty_matches_no_crash(tmp_path):
    mn = _load_mnemos()
    store = tmp_path / "snapshots"
    written = mn.ingest([], "2026-11-07T10:00:00Z", store)
    assert written == []
    assert mn.load_snapshots(store) == []
    json_path = mn.export_json(store, tmp_path / "exports" / "snapshots.json")
    csv_path = mn.export_csv(store, tmp_path / "exports" / "snapshots.csv")
    assert mn.load_export_json(json_path)["snapshots"] == []
    assert mn.load_export_csv(csv_path) == []


def test_match_fixture_ingests(tmp_path):
    mn = _load_mnemos()
    match = json.loads((REPO / "tests" / "fixtures" / "json" / "match.json").read_text(encoding="utf-8"))
    validate_instance(match, "schema_match.json")
    written = mn.ingest([match], "2026-11-07T10:00:00Z", tmp_path / "snapshots")
    assert len(written) == 1
    snap = mn.load_snapshots(tmp_path / "snapshots")[0]
    assert snap["match_key"] == match["match_key"]
    assert len(snap["points"]) == 1
    assert snap["points"][0]["index"] == "predictlix"
    assert snap["points"][0]["pick"] == "1"


def test_run_writes_snapshots_and_export(tmp_path):
    src = tmp_path / "IN"
    out = tmp_path / "OUT"
    snaps = tmp_path / "snapshots"
    exports = tmp_path / "exports"
    src.mkdir()
    match = _match(1.85)
    (src / "match_one.json").write_text(json.dumps(match, indent=2) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--in",
        str(src),
        "--out",
        str(out),
        "--snapshots",
        str(snaps),
        "--exports",
        str(exports),
        "--captured-at",
        "2026-11-07T10:00:00Z",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln]
    assert any("snap_" in ln for ln in lines)
    assert (exports / "snapshots.json").is_file()
    assert (exports / "snapshots.csv").is_file()
    bundle = json.loads((exports / "snapshots.json").read_text(encoding="utf-8"))
    assert len(bundle["snapshots"][0]["points"]) == 1
    copied = list(out.glob("snap_*.json"))
    assert len(copied) == 1
