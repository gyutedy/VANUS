#!/usr/bin/env python3
"""
SIGNAL — export agrege pour greffe externe (vanus.signal.v1).
=============================================================
Ne remplace rien : evolution_*.json et alert_*.json restent produits a
l'identique pour CELL et CIPHER. On AJOUTE une vue par match, tous marches,
avec ouverture/cloture horodatees et couverture declaree.

Regles tenues :
  - absent = null, jamais 0 ;
  - Pinnacle seulement si un point existant la porte deja ;
  - consensus : 2 index alignes = alarme, tous presents = jackpot ;
  - aucune probabilite produite ici. On agrege des observations.

Usage :
  python signals_export.py --in F02_MNEMOS/OUT --out SHARED/OUT/signals --slate 2026-11-09
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT = "vanus.signal.v1"
INDEX_ORDER = ("predictlix", "dailysportpick", "metapred", "footinsights", "besoccer", "vitibet")
INDEX_FIELDS = {"1x2": ("home", "draw", "away"), "ou_2_5": ("over_2_5", "under_2_5"),
                "btts": ("btts_yes", "btts_no"), "mt": ("mt_home", "mt_equal", "mt_away")}
PICK_WORDS = {
    "home": "home", "1": "home", "domicile": "home",
    "draw": "draw", "x": "draw", "nul": "draw",
    "away": "away", "2": "away", "exterieur": "away",
    "over": "over_2_5", "plus": "over_2_5", "o2.5": "over_2_5",
    "under": "under_2_5", "moins": "under_2_5", "u2.5": "under_2_5",
    "btts": "btts_yes", "btts_yes": "btts_yes", "btts_no": "btts_no",
    "mt1": "mt_home", "mte": "mt_equal", "mt2": "mt_away",
}
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm(value: Any) -> str:
    return _NON_ALNUM.sub("", str(value or "").lower())


def match_key(home: str, away: str, date: str | None = None) -> str:
    """Meme convention que F01 SCRYER : alnum minuscule, triee, date en suffixe."""
    h, a = _norm(home), _norm(away)
    base = "_".join(sorted([h, a]))
    return f"{base}_{date}" if date else base


def canon_pick(raw: Any) -> str | None:
    key = str(raw or "").strip().lower().replace(" ", "")
    if key in PICK_WORDS:
        return PICK_WORDS[key]
    norm = _norm(key)
    return PICK_WORDS.get(norm)


def _fnum(raw: Any) -> float | None:
    try:
        val = float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return val if val > 1.0 else None


def load_snapshots(src: Path) -> list[dict[str, Any]]:
    if src.is_file():
        data = json.loads(src.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else [data]
    out: list[dict[str, Any]] = []
    if not src.is_dir():
        return out
    for path in sorted(src.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append(data)
    return out


def _points(snap: dict[str, Any]) -> list[dict[str, Any]]:
    pts = snap.get("points")
    return [p for p in (pts or []) if isinstance(p, dict)]


def _odds_of(point: dict[str, Any]) -> dict[str, Any]:
    odds = point.get("odds")
    return odds if isinstance(odds, dict) else {}


def _price(odds: dict[str, Any], market: str, selection: str) -> float | None:
    """Recherche tolerante : champ exact, puis cle normalisee, puis champ imbrique."""
    if market in odds and isinstance(odds[market], dict):
        return _fnum(odds[market].get(selection))
    for key in (selection, selection.replace("_", "."), selection.replace("_", "")):
        val = _fnum(odds.get(key))
        if val is not None:
            return val
    for nested in odds.values():
        if isinstance(nested, dict):
            val = _fnum(nested.get(selection))
            if val is not None:
                return val
    return None


def _series(points: list[dict[str, Any]], market: str, selection: str):
    """Liste [(at, prix)] triee. Les trous sont omis, jamais remplaces."""
    out = []
    for p in points:
        at = str(p.get("captured_at") or "")
        if not at:
            continue
        val = _price(_odds_of(p), market, selection)
        if val is not None:
            out.append((at, val))
    out.sort(key=lambda x: x[0])
    return out


def _triplet(points, market, keys):
    rec = {"ouvert": {}, "cloture": {}, "at_ouverture": None, "at_cloture": None,
           "n_points": len(points)}
    first_at, first, last_at, last = None, {}, None, {}
    for key in keys:
        serie = _series(points, market, key)
        if not serie:
            rec["ouvert"][key] = None
            rec["cloture"][key] = None
            continue
        rec["ouvert"][key] = serie[0][1]
        rec["cloture"][key] = serie[-1][1]
        last[key] = serie[-1][1]
        first[key] = serie[0][1]
        if last_at is None or serie[-1][0] > last_at:
            last_at = serie[-1][0]
        if first_at is None or serie[0][0] < first_at:
            first_at = serie[0][0]
    if all(v is None for v in rec["ouvert"].values()):
        return None
    rec["at_ouverture"] = first_at
    rec["at_cloture"] = last_at
    return rec


def _paire(points, market, over_key, under_key):
    rec = {"ouvert": None, "cloture": None, "at_ouverture": None, "at_cloture": None,
           "n_points": len(points)}
    over = _series(points, market, over_key)
    under = _series(points, market, under_key)
    if over:
        rec["ouvert"] = over[0][1]
        rec["cloture"] = over[-1][1]
        rec["at_ouverture"] = over[0][0]
        rec["at_cloture"] = over[-1][0]
    if under:
        rec["at_ouverture"] = min(filter(None, [rec["at_ouverture"], under[0][0]]))
        rec["at_cloture"] = max(filter(None, [rec["at_cloture"], under[-1][0]]))
    return rec if (over or under) else None


def _pinnacle(points):
    """Pinnacle seulement si elle apparait deja dans un point. Sinon null."""
    for p in points:
        odds = _odds_of(p)
        for key in ("pinnacle", "pin", "pn"):
            val = _fnum(odds.get(key))
            if val is not None:
                return {"sharp": val, "sharp_issue": None, "sharp_marche": "1x2",
                        "source": key, "at": str(p.get("captured_at") or "") or None}
    return {"sharp": None, "sharp_issue": None, "sharp_marche": None,
            "source": None, "at": None}


def _consensus(picks: dict[str, str | None], presents: list[str]):
    votes = [v for v in picks.values() if v]
    if not votes:
        return {"selection": None, "n": 0, "found": len(presents),
                "niveau": "aucun", "agreeing": []}
    tally: dict[str, list[str]] = {}
    for index, pick in picks.items():
        if pick:
            tally.setdefault(pick, []).append(index)
    best_sel, best_idx = None, []
    for sel, idx in tally.items():
        if len(idx) > len(best_idx):
            best_sel, best_idx = sel, idx
    n = len(best_idx)
    if n >= len(INDEX_ORDER) and len(presents) >= len(INDEX_ORDER):
        niveau = "jackpot"
    elif n >= 2:
        niveau = "alarme"
    elif n == 1:
        niveau = "isole"
    else:
        niveau = "aucun"
    return {"selection": best_sel, "n": n, "found": len(presents),
            "niveau": niveau, "agreeing": sorted(best_idx)}


def _couverture(presents: list[str], marches: int):
    n = len(presents)
    if n >= 4 and marches >= 3:
        niveau = "haute"
    elif n >= 2 and marches >= 2:
        niveau = "moyenne"
    else:
        niveau = "faible"
    return {"n_index": len(INDEX_ORDER), "n_presents": n,
            "n_marches": marches, "niveaux": niveau}


def build(snapshot: dict[str, Any]) -> dict[str, Any]:
    key = str(snapshot.get("match_key") or "")
    home = str(snapshot.get("home") or "")
    away = str(snapshot.get("away") or "")
    date = str(snapshot.get("slate_date") or "")[:10]
    if not key and home and away:
        key = match_key(home, away, date or None)
    points = _points(snapshot)
    holes: list[str] = []
    per_index: dict[str, list[dict[str, Any]]] = {}
    for p in points:
        idx = str(p.get("index") or "")
        if idx:
            per_index.setdefault(idx, []).append(p)
    indexes: dict[str, Any] = {}
    picks: dict[str, str | None] = {}
    for idx in INDEX_ORDER:
        pts = per_index.get(idx) or []
        if not pts:
            indexes[idx] = None
            picks[idx] = None
            continue
        last = pts[-1]
        pick = canon_pick(last.get("pick"))
        if pick is None:
            pick = canon_pick((last.get("odds") or {}).get("pick"))
        pct = _fnum(last.get("model_pct"))
        indexes[idx] = {"pick": pick, "model_pct": pct,
                        "at": str(last.get("captured_at") or "") or None}
        picks[idx] = pick
    presents = [i for i in INDEX_ORDER if indexes.get(i)]
    if not presents:
        holes.append("aucun_index")
    marches = {}
    tri = _triplet(points, "1x2", INDEX_FIELDS["1x2"])
    if tri:
        marches["1x2"] = tri
    else:
        holes.append("cotes_1x2")
    paire = _paire(points, "ou_2_5", "over_2_5", "under_2_5")
    if paire:
        marches["ou_2_5"] = paire
    else:
        holes.append("cotes_ou_2_5")
    bt = _paire(points, "btts", "btts_yes", "btts_no")
    if bt:
        marches["btts"] = bt
    tri_mt = _triplet(points, "mt", INDEX_FIELDS["mt"])
    if tri_mt:
        marches["mt"] = tri_mt
    consensus = _consensus(picks, presents)
    return {
        "match_key": key,
        "competition": str(snapshot.get("competition") or ""),
        "home": home,
        "away": away,
        "kickoff": str(snapshot.get("kickoff") or ""),
        "indexes": indexes,
        "consensus": consensus,
        "marches": marches,
        "reference": _pinnacle(points),
        "couverture": _couverture(presents, len(marches)),
        "holes": holes,
    }


def write(blob: dict[str, Any], out_dir: Path, slate: str | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    day = slate or blob.get("slate_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    written = []
    target = out_dir / f"signals_{day}.json"
    body = dict(blob)
    body["contract"] = CONTRACT
    body["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body["slate_date"] = day
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(target)
    written.append(target)
    latest = out_dir / "latest.json"
    tmp2 = latest.with_suffix(".json.tmp")
    tmp2.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp2.replace(latest)
    written.append(latest)
    return written


def aggregate(snapshots: list[dict[str, Any]], out_dir: Path, slate: str | None = None):
    matches: dict[str, Any] = {}
    holes: list[str] = []
    vus: set[str] = set()
    for snap in snapshots:
        if not isinstance(snap, dict):
            continue
        rec = build(snap)
        if not rec.get("match_key"):
            holes.append("match_key_absent")
            continue
        matches[rec["match_key"]] = rec
        for idx, val in (rec.get("indexes") or {}).items():
            if val:
                vus.add(idx)
    blob = {"contract": CONTRACT, "matches": matches,
            "indexes_vus": sorted(vus), "holes": holes}
    return blob, write(blob, out_dir, slate=slate)


def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="F03 — export vanus.signal.v1")
    ap.add_argument("--in", dest="src", default=str(here.parent / "F02_MNEMOS" / "OUT"))
    ap.add_argument("--out", default=str(here.parent / "SHARED" / "OUT" / "signals"))
    ap.add_argument("--slate", default=None)
    args = ap.parse_args(argv)
    src = Path(args.src)
    if not src.exists():
        print(f"missing in: {src}")
        return 2
    blob, written = aggregate(load_snapshots(src), Path(args.out), slate=args.slate)
    print(f"[SIGNAL] {len(blob['matches'])} match(s) — index vus : {blob['indexes_vus']}")
    for path in written:
        print(path)
    if blob.get("holes"):
        print(f"trous : {blob['holes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
