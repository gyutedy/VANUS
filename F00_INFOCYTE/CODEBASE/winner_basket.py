#!/usr/bin/env python3
"""
WINNER BASKET — capteur NBA winner.bet (lecture seule, stdlib).
==============================================================
Marches : 2 Way (ml_1/ml_2), Total Spreads (ligne + under/over).
FT 1X2 ignore : pas de X au basket (prolongation).
Absent = null + trou. HTML archive avant parsing. Aucune probabilite.
Usage :
  python winner_basket.py --url <page NBA> --out SHARED/OUT/slates/winner_basket.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from winner_common import fetch, match_key, _num, _line, _norm
from winner_order import build_slate

CONTRACT = "vanus.slate.v1"
INDEX = "winner_basket"
SPORT = "basket"
SOURCE_URL = "https://winner.bet/en/sportsbook/league/basketball/usa/nba"

_ROW = re.compile(r"<tr[^>]*class=[\"'][^\"']*event-row[^\"']*[^>]*>(.*?)</tr>", re.S)
_TEAMS = re.compile(r"class=[\"'][^\"']*event-teams[^\"']*[^>]*>(.*?)<", re.S)
_TIME = re.compile(r"(\d{2}:\d{2})")
_MID = re.compile(r"#(\d+)")
_ODD = re.compile(r">\s*([0-9]+[.,][0-9]{2})\s*<")


def _cells(row_html):
    return [c for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]


def parse(html):
    """HTML -> (matchs, trous). Toute cellule manquante = None + trou."""
    holes, out = [], []
    rows = _ROW.findall(html)
    if not rows:
        return [], ["selecteur_ligne_absent"]
    for row in rows:
        raw = _TEAMS.search(row)
        teams_raw = _norm(raw.group(1)) if raw else ""
        parts = [t for t in re.split(r"\s+vs\.?\s+|\s+-\s+", teams_raw) if t]
        home = parts[0] if len(parts) > 1 else None
        away = parts[1] if len(parts) > 1 else None
        if not home or not away:
            holes.append("equipes_absentes")
            continue
        mtime, mid = _TIME.search(row), _MID.search(row)
        odds = [_num(o) for o in _ODD.findall(row)]
        ml1 = odds[0] if len(odds) > 0 else None
        ml2 = odds[1] if len(odds) > 1 else None
        rest = odds[2:]
        rest = rest[3:] if len(rest) >= 3 else rest  # FT 1X2 diagnostique ignore
        under = rest[0] if len(rest) > 0 else None
        over = rest[1] if len(rest) > 1 else None
        tl_raw = re.search(r"([0-9]{3}[.,][05])", row)
        tline = _line(_norm(tl_raw.group(1))) if tl_raw else None
        out.append({
            "match_key": match_key(home, away),
            "index": INDEX,
            "sport": SPORT,
            "competition": "NBA",
            "home": home,
            "away": away,
            "kickoff": mtime.group(1) if mtime else None,
            "source_event_id": mid.group(1) if mid else None,
            "odds": {"ml_1": ml1, "ml_2": ml2, "total_line": tline,
                     "total_under": under, "total_over": over},
            "diagnostic_only": [],
            "holes": [h for h in [
                "ml_absente" if ml1 is None or ml2 is None else "",
                "total_absent" if under is None or over is None or tline is None else "",
            ] if h],
        })
    return out, holes


def build(html):
    matches, holes = parse(html)
    return build_slate(CONTRACT, INDEX, SPORT, SOURCE_URL, matches, holes)


def main():
    ap = argparse.ArgumentParser(description="F00 capteur Winner basket (lecture seule)")
    ap.add_argument("--url", default=SOURCE_URL)
    ap.add_argument("--archive", default="ARCHIVUM/cache/winner")
    ap.add_argument("--out", default="SHARED/OUT/slates/winner_basket.json")
    args = ap.parse_args()
    html, holes = fetch(args.url, args.archive)
    if not html:
        blob = build_slate(CONTRACT, INDEX, SPORT, args.url, [], holes)
    else:
        blob = build(html)
        blob["holes"] = list(dict.fromkeys(blob["holes"] + holes))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[WINNER-BASKET] {len(blob['matches'])} match(s), {len(blob['holes'])} trou(s) -> {out}")


if __name__ == "__main__":
    main()
