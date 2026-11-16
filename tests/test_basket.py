from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F03_SPECULUM" / "CODEBASE"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _sx():
    return _load("signals_export_basket", CODEBASE / "signals_export.py")


def _vb():
    return _load("vitibet_basket", REPO / "F00_INFOCYTE" / "CODEBASE" / "vitibet_basket.py")


def _snap(index, pick):
    return {
        "match_key": "celtics_mavericks_2026-11-16",
        "home": "Boston Celtics",
        "away": "Dallas Mavericks",
        "competition": "NBA",
        "slate_date": "2026-11-16",
        "kickoff": "2026-11-16T00:00:00Z",
        "points": [{
            "index": index,
            "captured_at": "2026-11-16T10:00:00Z",
            "pick": pick,
            "odds": {"home": 1.9, "away": 2.1},
        }],
    }


def test_schema_sport_optionnel():
    schema = json.loads((REPO / "CONTRACTS" / "schema_signal.json").read_text(encoding="utf-8"))
    prop = schema["properties"]["sport"]
    assert prop["type"] == "string"
    assert set(prop["enum"]) == {"foot", "basket"}
    assert prop["default"] == "foot"


def test_index_order_foot_intact():
    sx = _sx()
    assert sx.INDEX_ORDER == ("predictlix", "dailysportpick", "metapred",
                              "footinsights", "besoccer", "vitibet")
    assert sx.BASKET_INDEX_ORDER == ("vitibet_basket", "sportsai_basket", "oddspedia_basket")
    assert sx.BASKET_FIELDS["ml"] == ("home", "away")


def test_canon_pick_basket_sans_nul():
    sx = _sx()
    assert sx.canon_pick_basket("1") == "home"
    assert sx.canon_pick_basket("2") == "away"
    assert sx.canon_pick_basket("X") is None
    assert sx.canon_pick_basket("over") == "total_over"


def test_basket_consensus_alarme_et_isole():
    sx = _sx()
    deux = sx.build_basket({
        "match_key": "a_b", "home": "A", "away": "B", "slate_date": "2026-11-16",
        "points": [
            {"index": "vitibet_basket", "captured_at": "2026-11-16T10:00:00Z", "pick": "1"},
            {"index": "sportsai_basket", "captured_at": "2026-11-16T11:00:00Z", "pick": "home"},
        ],
    })
    assert deux["consensus"]["niveau"] == "alarme"
    assert deux["consensus"]["n"] == 2
    un = sx.build_basket(_snap("vitibet_basket", "2"))
    assert un["consensus"]["niveau"] == "isole"
    assert un["consensus"]["n"] == 1


def test_export_basket_sport_dans_fichier(tmp_path):
    sx = _sx()
    blob, written = sx.aggregate_basket([_snap("vitibet_basket", "1")], tmp_path,
                                        slate="2026-11-16")
    assert blob["sport"] == "basket"
    data = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert data["contract"] == "vanus.signal.v1"
    assert data["sport"] == "basket"
    assert written


def test_export_foot_reste_compatible(tmp_path):
    sx = _sx()
    blob, _ = sx.aggregate([], tmp_path, slate="2026-11-16")
    assert blob["sport"] == "foot"
    data = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert data["sport"] == "foot"


HTML = """
<div class='livescore-league top-league'>
  <span class='league-title'>United States: NBA</span>
  <a class='livescore-match-row' data-fid='519725'>
    <span class='local-time' data-time='2026-11-16 00:00:00'>00:00</span>
    <span class='livescore-team-name'>Boston Celtics</span>
    <span class='livescore-team-name'>Dallas Mavericks</span>
    <div class='prob-head'>1</div><div class='prob-val'>82%</div>
    <div class='prob-head'>2</div><div class='prob-val'>12%</div>
    <span class='tip-indicator-circle'>1</span>
  </a>
</div>
"""


def test_vitibet_basket_parse():
    vb = _vb()
    slate = vb.parse_html(HTML, slate_date="2026-11-16", captured_at="2026-11-16T10:00:00Z")
    assert slate["index"] == "vitibet_basket"
    assert slate["sport"] == "basket"
    assert len(slate["matches"]) == 1
    row = slate["matches"][0]
    assert row["home"] == "Boston Celtics"
    assert row["away"] == "Dallas Mavericks"
    assert row["pick"] == "home"
    assert 0.8 < row["model_pct"] < 0.9


def test_vitibet_basket_sans_x():
    vb = _vb()
    html = HTML.replace(">1</span>", ">X</span>")
    slate = vb.parse_html(html, slate_date="2026-11-16")
    assert slate["matches"][0]["pick"] is None


def test_signaux_basket_initial():
    p = REPO / "SHARED" / "OUT" / "signals-basket" / "latest.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["contract"] == "vanus.signal.v1"
    assert data["sport"] == "basket"
    assert data["matches"] == {}
    assert data["holes"]
