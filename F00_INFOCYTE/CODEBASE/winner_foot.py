#!/usr/bin/env python3
"""
WINNER FOOT — capteur soccer winner.bet (lecture seule, stdlib).
===============================================================
Marches : 1X2, Under/Over 2.5, HSH (Highest Scoring Half).
Le HSH est tarife au template (3.10/3.00/2.02 sur des matchs sans
rapport, marge ~15.1 %) : capture pour la trace, diagnostic_only,
JAMAIS un ticket. Absent = null + trou. Aucune probabilite.
Usage :
  python winner_foot.py --url <page Upcoming> --out SHARED/OUT/slates/winner_foot.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from winner_common import fetch, match_key, _num, _norm
from winner_order import build_slate

CONTRACT = "vanus.slate.v1"
INDEX = "winner_foot"
SPORT = "foot"
SOURCE_URL = "https://winner.bet/en/sportsbook/upcoming"

_ROW = re.compile(r"<tr[^>]*class=[\"'][^\"']*event-row[^\"']*[^>]*>(.*?)</tr>", re.S)
_TEAMS = re.compile(r"class=[\"'][^\"']*event-teams[^\"']*[^>]*>(.*?)<", re.S)
_LEAGUE = re.compile(r"class=[\"'][^\"']*league-title[^\"']*[^>]*>([^<]+)<", re.I)
_TIME = re.compile(r"(\d{2}:\d{2})")
_MID = re.compile(r"#(\d+)")
_ODD = re.compile(r">\s*([0-9]+[.,][0-9]{2})\s*<")


def parse(html):
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
        lg = _LEAGUE.search(row)
        mtime, mid = _TIME.search(row), _MID.search(row)
        odds = [_num(o) for o in _ODD.findall(row)]
        g = lambda i: odds[i] if len(odds) > i else None
        out.append({
            "match_key": match_key(home, away),
            "index": INDEX,
            "sport": SPORT,
            "competition": _norm(lg.group(1)) if lg else None,
            "home": home,
            "away": away,
            "kickoff": mtime.group(1) if mtime else None,
            "source_event_id": mid.group(1) if mid else None,
            "odds": {"home": g(0), "draw": g(1), "away": g(2),
                     "under_2_5": g(3), "over_2_5": g(4),
                     "hsh_first": g(5), "hsh_equal": g(6), "hsh_second": g(7)},
            "diagnostic_only": ["hsh_first", "hsh_equal", "hsh_second"],
            "holes": [h for h in [
                "1x2_absente" if any(g(i) is None for i in (0, 1, 2)) else "",
                "ou25_absente" if any(g(i) is None for i in (3, 4)) else "",
                "hsh_absente" if any(g(i) is None for i in (5, 6, 7)) else "",
            ] if h],
        })
    return out, holes


def build(html):
    matches, holes = parse(html)
    return build_slate(CONTRACT, INDEX, SPORT, SOURCE_URL, matches, holes)


def main():
    ap = argparse.ArgumentParser(description="F00 capteur Winner foot (lecture seule)")
    ap.add_argument("--url", default=SOURCE_URL)
    ap.add_argument("--archive", default="ARCHIVUM/cache/winner")
    ap.add_argument("--out", default="SHARED/OUT/slates/winner_foot.json")
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
    print(f"[WINNER-FOOT] {len(blob['matches'])} match(s), {len(blob['holes'])} trou(s) -> {out}")


if __name__ == "__main__":
    main()
