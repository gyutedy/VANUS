from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F03_SPECULUM" / "CODEBASE"
KEY = "laliga:2026-11-07:2000:athletic-club:valencia"


def _load():
    path = CODEBASE / "speculum.py"
    spec = importlib.util.spec_from_file_location("speculum", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _pt(at: str, index: str, home: float, pinnacle: float | None = None) -> dict:
    odds: dict = {"1x2": {"home": home, "draw": 3.4, "away": 4.2}}
    if pinnacle is not None:
        odds["pinnacle"] = {"price": pinnacle}
    return {"captured_at": at, "index": index, "pick": "1", "odds": odds}


def _snap(points: list[dict]) -> dict:
    return {
        "match_key": KEY,
        "competition": "LaLiga",
        "slate_date": "2026-11-07",
        "home": "Athletic Club",
        "away": "Valencia",
        "kickoff": "2026-11-07T20:00:00Z",
        "points": points,
    }


def test_three_timestamps_three_points():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.85),
            _pt("2026-11-07T14:00:00Z", "predictlix", 1.80),
        ]
    )
    evo = sp.evolve(snap)
    validate_instance(evo, "schema_evolution.json")
    assert evo["market"] == "1x2"
    assert evo["selection"] == "home"
    line = next(ln for ln in evo["lines"] if ln["index"] == "predictlix")
    assert len(line["points"]) == 3
    assert [p["at"] for p in line["points"]] == [
        "2026-11-07T10:00:00Z",
        "2026-11-07T12:00:00Z",
        "2026-11-07T14:00:00Z",
    ]
    assert [p["odds"] for p in line["points"]] == [1.90, 1.85, 1.80]


def test_two_of_three_is_alarm_not_jackpot():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
            _pt("2026-11-07T10:00:00Z", "dailysportpick", 2.00),
            _pt("2026-11-07T12:00:00Z", "dailysportpick", 2.10),
        ]
    )
    evo = sp.evolve(snap)
    alert = sp.assess(evo)
    assert alert is not None
    validate_instance(alert, "schema_alert.json")
    assert alert["level"] == "alarm"
    assert alert["direction"] == "shortening"
    assert set(alert["agreeing"]) == {"predictlix", "metapred"}
    assert set(alert["found"]) == {"predictlix", "metapred", "dailysportpick"}
    assert alert["level"] != "jackpot"


def test_one_of_three_is_no_alert():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T10:00:00Z", "dailysportpick", 2.00),
            _pt("2026-11-07T12:00:00Z", "dailysportpick", 2.00),
        ]
    )
    assert sp.assess(sp.evolve(snap)) is None


def test_same_fingerprint_no_second_alert():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
        ]
    )
    evo = sp.evolve(snap)
    seen: set[str] = set()
    first = sp.assess(evo, seen)
    second = sp.assess(evo, seen)
    assert first is not None
    validate_instance(first, "schema_alert.json")
    assert second is None
    assert first["fingerprint"] in seen


def test_pinnacle_absent_is_not_disagreement():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
        ]
    )
    evo = sp.evolve(snap)
    assert all(ln["role"] != "pinnacle_ref" for ln in evo["lines"])
    alert = sp.assess(evo)
    assert alert is not None
    validate_instance(alert, "schema_alert.json")
    assert alert["pinnacle_agrees"] is None
    assert "pinnacle" not in alert["found"]
    assert alert["level"] == "jackpot"


def test_all_found_is_jackpot():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
            _pt("2026-11-07T10:00:00Z", "dailysportpick", 2.00),
            _pt("2026-11-07T12:00:00Z", "dailysportpick", 1.90),
        ]
    )
    alert = sp.assess(sp.evolve(snap))
    assert alert is not None
    validate_instance(alert, "schema_alert.json")
    assert alert["level"] == "jackpot"
    assert set(alert["agreeing"]) == set(alert["found"])


def test_alarm_to_jackpot_emits_second():
    sp = _load()
    seen: set[str] = set()
    two = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
            _pt("2026-11-07T10:00:00Z", "dailysportpick", 2.00),
            _pt("2026-11-07T12:00:00Z", "dailysportpick", 2.10),
        ]
    )
    alarm = sp.assess(sp.evolve(two), seen)
    assert alarm is not None and alarm["level"] == "alarm"
    all_three = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
            _pt("2026-11-07T10:00:00Z", "dailysportpick", 2.00),
            _pt("2026-11-07T14:00:00Z", "dailysportpick", 1.85),
        ]
    )
    jackpot = sp.assess(sp.evolve(all_three), seen)
    assert jackpot is not None
    validate_instance(jackpot, "schema_alert.json")
    assert jackpot["level"] == "jackpot"
    assert jackpot["fingerprint"] != alarm["fingerprint"]


def test_pinnacle_ref_line_if_already_in_odds():
    sp = _load()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90, pinnacle=1.88),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80, pinnacle=1.84),
        ]
    )
    evo = sp.evolve(snap)
    validate_instance(evo, "schema_evolution.json")
    pin = next(ln for ln in evo["lines"] if ln["role"] == "pinnacle_ref")
    assert pin["index"] == "pinnacle"
    assert [p["odds"] for p in pin["points"]] == [1.88, 1.84]


def test_empty_snapshot_no_crash():
    sp = _load()
    evo = sp.evolve(_snap([]))
    validate_instance(evo, "schema_evolution.json")
    assert evo["lines"] == []
    assert sp.assess(evo) is None


def test_run_writes_evolution_and_alert(tmp_path):
    src = tmp_path / "IN"
    out = tmp_path / "OUT"
    src.mkdir()
    snap = _snap(
        [
            _pt("2026-11-07T10:00:00Z", "predictlix", 1.90),
            _pt("2026-11-07T12:00:00Z", "predictlix", 1.80),
            _pt("2026-11-07T10:00:00Z", "metapred", 1.88),
            _pt("2026-11-07T12:00:00Z", "metapred", 1.78),
        ]
    )
    (src / "snap_one.json").write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--in",
        str(src),
        "--out",
        str(out),
        "--seen",
        str(tmp_path / "seen.json"),
        "--signal-out",
        str(tmp_path / "signals"),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    names = {Path(line).name for line in proc.stdout.strip().splitlines() if line}
    assert any(n.startswith("evolution_") for n in names)
    assert any(n.startswith("alert_") for n in names)
    evo = json.loads(next(out.glob("evolution_*.json")).read_text(encoding="utf-8"))
    alert = json.loads(next(out.glob("alert_*.json")).read_text(encoding="utf-8"))
    validate_instance(evo, "schema_evolution.json")
    validate_instance(alert, "schema_alert.json")
    proc2 = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    names2 = {Path(line).name for line in proc2.stdout.strip().splitlines() if line}
    assert not any(n.startswith("alert_") for n in names2)
