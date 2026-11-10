from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F03_SPECULUM" / "CODEBASE"


def _load():
    path = CODEBASE / "signals_export.py"
    spec = importlib.util.spec_from_file_location("signals_export", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _snap(points, **kw):
    base = {
        "match_key": "arsenal_chelsea_2026-11-09",
        "home": "Arsenal",
        "away": "Chelsea",
        "competition": "Premier League",
        "slate_date": "2026-11-09",
        "kickoff": "2026-11-09T20:00:00Z",
        "points": points,
    }
    base.update(kw)
    return base


def test_index_muet_nul():
    sx = _load()
    snap = _snap(
        [
            {
                "index": "predictlix",
                "captured_at": "2026-11-09T10:00:00Z",
                "pick": "home",
                "odds": {"1x2": {"home": 1.9, "draw": 3.5, "away": 4.2}},
            }
        ]
    )
    rec = sx.build(snap)
    assert rec["indexes"]["metapred"] is None
    assert "ou_2_5" not in rec["marches"]
    assert "cotes_ou_2_5" in rec["holes"]


def test_consensus_alarme():
    sx = _load()
    pts = [
        {"index": "predictlix", "captured_at": "2026-11-09T10:00:00Z", "pick": "home"},
        {"index": "metapred", "captured_at": "2026-11-09T12:00:00Z", "pick": "1"},
    ]
    rec = sx.build(_snap(pts))
    assert rec["consensus"]["niveau"] == "alarme"
    assert rec["consensus"]["n"] == 2
    assert rec["consensus"]["found"] == 2


def test_un_seul_ne_vote_pas_consensus():
    sx = _load()
    pts = [{"index": "predictlix", "captured_at": "2026-11-09T10:00:00Z", "pick": "away"}]
    rec = sx.build(_snap(pts))
    assert rec["consensus"]["niveau"] == "isole"
    assert rec["consensus"]["niveau"] != "alarme"


def test_pinnacle_non_cherchee():
    sx = _load()
    pts = [
        {
            "index": "predictlix",
            "captured_at": "2026-11-09T10:00:00Z",
            "pick": "home",
            "odds": {"1x2": {"home": 1.9}},
        }
    ]
    rec = sx.build(_snap(pts))
    assert rec["reference"]["sharp"] is None
    assert rec["reference"]["source"] is None


def test_pinnacle_si_deja_la():
    sx = _load()
    pts = [
        {
            "index": "predictlix",
            "captured_at": "2026-11-09T10:00:00Z",
            "pick": "home",
            "odds": {"1x2": {"home": 1.9}, "pinnacle": 1.95},
        }
    ]
    rec = sx.build(_snap(pts))
    assert rec["reference"]["sharp"] == 1.95


def test_ouverture_cloture():
    sx = _load()
    pts = [
        {
            "index": "predictlix",
            "captured_at": "2026-11-09T10:00:00Z",
            "pick": "home",
            "odds": {"1x2": {"home": 2.10, "draw": 3.4, "away": 3.8}},
        },
        {
            "index": "predictlix",
            "captured_at": "2026-11-09T14:00:00Z",
            "pick": "home",
            "odds": {"1x2": {"home": 1.85, "draw": 3.6, "away": 4.4}},
        },
    ]
    rec = sx.build(_snap(pts))
    tri = rec["marches"]["1x2"]
    assert tri["ouvert"]["home"] == 2.10
    assert tri["cloture"]["home"] == 1.85
    assert tri["at_cloture"] == "2026-11-09T14:00:00Z"


def test_ecriture_atomique(tmp_path):
    sx = _load()
    blob, written = sx.aggregate([_snap([])], tmp_path, slate="2026-11-09")
    latest = tmp_path / "latest.json"
    assert (tmp_path / "signals_2026-11-09.json").is_file()
    assert latest.is_file()
    data = json.loads(latest.read_text(encoding="utf-8"))
    assert data.get("contract") == "vanus.signal.v1"
    assert blob["contract"] == "vanus.signal.v1"
    assert written


def test_pick_inconnu():
    sx = _load()
    assert sx.canon_pick("peut-etre") is None
    assert sx.canon_pick("Plus") == "over_2_5"


def test_no_import_other_frigates():
    source = (CODEBASE / "signals_export.py").read_text(encoding="utf-8")
    assert "F00_" not in source
    assert "F01_" not in source
    assert "F04_" not in source
    assert "F05_" not in source
    assert "perturabo" not in source.lower()
    assert "urllib.request" not in source
    assert "requests" not in source
