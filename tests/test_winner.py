#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capteur Winner — E2E offline : fixtures, contrat, trous, zero proba,
HSH diagnostic. Style maison : compteur PASS/N, exit non-zero si echec."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "F00_INFOCYTE" / "CODEBASE"
FIX = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(CODE))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, CODE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


winner_common = _load("winner_common")
winner_basket = _load("winner_basket")
winner_foot = _load("winner_foot")
winner_order = _load("winner_order")

PASS = []
N = [0]


def _by_key(blob, key):
    return next(m for m in blob["matches"] if m["match_key"] == key)


def check(name, cond):
    N[0] += 1
    if cond:
        PASS.append(name)
    else:
        print("FAIL:", name)
        raise AssertionError(name)


def run_checks():
    PASS.clear()
    N[0] = 0
    with open(FIX / "winner_basket.html", encoding="utf-8") as f:
        blob = winner_basket.build(f.read())
    with open(FIX / "winner_foot.html", encoding="utf-8") as f:
        fblob = winner_foot.build(f.read())

    check("basket contrat", blob["contract"] == "vanus.slate.v1")
    check("basket index/sport", blob["index"] == "winner_basket" and blob["sport"] == "basket")
    check("basket 4 lignes lues", len(blob["matches"]) == 4)
    m1 = _by_key(blob, "atlantahawks_detroitpistons")
    check("basket equipes", m1["home"] == "Atlanta Hawks" and m1["away"] == "Detroit Pistons")
    check("basket match_key trie", m1["match_key"] == "atlantahawks_detroitpistons")
    check("basket ML capturee", m1["odds"]["ml_1"] == 2.08 and m1["odds"]["ml_2"] == 1.73)
    check("basket total ligne+U/O", m1["odds"]["total_line"] == 226.5
          and m1["odds"]["total_under"] == 1.80 and m1["odds"]["total_over"] == 1.87)
    check("basket pas de X produit", "draw" not in m1["odds"] and "x" not in m1["odds"])
    check("basket aucune probabilite", not any("p_" in k or "prob" in k
          for k in json.dumps(blob).lower().split('"')))
    check("basket FT1X2 ignore (pas de champ)", not any("ft" in k for k in m1["odds"]))
    m4 = _by_key(blob, "ghostteam_nobody")
    check("basket cote unique manquante -> trou", m4["odds"]["total_under"] is None
          and "total_absent" in m4["holes"])
    check("basket horodatage", blob["generated_at"].endswith("Z") or "+00:00" in blob["generated_at"])

    check("foot contrat", fblob["contract"] == "vanus.slate.v1")
    check("foot 3 lignes", len(fblob["matches"]) == 3)
    f1 = _by_key(fblob, "erzurumsporfk_goztepeizmir")
    check("foot 1X2", f1["odds"]["home"] == 2.57 and f1["odds"]["draw"] == 3.00
          and f1["odds"]["away"] == 2.57)
    check("foot OU 2.5", f1["odds"]["under_2_5"] == 1.60 and f1["odds"]["over_2_5"] == 2.15)
    check("foot HSH capture", f1["odds"]["hsh_first"] == 3.10
          and f1["odds"]["hsh_equal"] == 3.00 and f1["odds"]["hsh_second"] == 2.02)
    check("foot HSH diagnostic_only", set(f1["diagnostic_only"]) ==
          {"hsh_first", "hsh_equal", "hsh_second"})
    check("foot competition", f1["competition"] == "Turkiye - Super Lig")
    f3 = _by_key(fblob, "juventusturin_veneziafc")
    check("foot event_id absent = null", f3["source_event_id"] is None)

    check("match_key sans date", winner_common.match_key("Alpha", "Beta") == "alpha_beta")
    check("match_key trie", winner_common.match_key("Beta", "Alpha") == "alpha_beta")
    check("cote invalide -> None", winner_common._num("—") is None
          and winner_common._num("") is None and winner_common._num("0.95") is None)
    check("ligne parse", winner_common._line("226,5") == 226.5)
    check("order dedupe", len(winner_order.order_matches(
        [{"match_key": "a_b"}, {"match_key": "a_b"}])[0]) == 1)

    html, holes = winner_common.fetch("https://localhost:1/inaccessible", tempfile.mkdtemp())
    check("fetch echec = trou declare", html == "" and holes
          and holes[0].startswith("fetch_failed"))

    for mod in (winner_basket, winner_foot, winner_common, winner_order):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        check("heresie #11 " + mod.__name__, "perturabo" not in src.lower()
              and "breacher" not in src.lower())

    print(f"Capteur Winner : {len(PASS)}/{N[0]} PASS")
    return N[0] - len(PASS)


def test_winner_capteur():
    assert run_checks() == 0


if __name__ == "__main__":
    raise SystemExit(run_checks())
