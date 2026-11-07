from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

CONTRACT = "vanus.match.v1"
WINDOW_MINUTES = 45
FUZZY_THRESHOLD = 0.90
FILLERS = frozenset({"fc", "cf", "afc"})
INDEX_ORDER = (
    "predictlix",
    "dailysportpick",
    "metapred",
    "footinsights",
    "besoccer",
    "vitibet",
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_name(value: str) -> str:
    text = _strip_accents(value).lower()
    text = _NON_ALNUM.sub(" ", text)
    parts = [p for p in text.split() if p and p not in FILLERS]
    return " ".join(parts)


def name_slug(value: str) -> str:
    return normalize_name(value).replace(" ", "-") or "unknown"


def competition_slug(value: str) -> str:
    text = _strip_accents(value).lower()
    return _NON_ALNUM.sub("", text) or "unknown"


def load_aliases(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"teams": {}}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        return {"teams": {}}
    teams = raw.get("teams", raw)
    if not isinstance(teams, dict):
        return {"teams": {}}
    cleaned: dict[str, list[str]] = {}
    for key, val in teams.items():
        if isinstance(val, list):
            cleaned[str(key)] = [str(x) for x in val]
        elif isinstance(val, str):
            cleaned[str(key)] = [val]
    return {"teams": cleaned}


def save_aliases(data: dict[str, Any], path: Path) -> None:
    payload = {"teams": dict(data.get("teams") or {})}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_slates(src: Path) -> list[dict[str, Any]]:
    if src.is_file():
        data = json.loads(src.read_text(encoding="utf-8"))
        return [data] if isinstance(data, dict) and data.get("contract") == "vanus.slate.v1" else []
    slates: list[dict[str, Any]] = []
    if not src.is_dir():
        return slates
    for path in sorted(src.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("contract") == "vanus.slate.v1":
            slates.append(data)
    return slates


def write_match(match: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _NON_ALNUM.sub("_", match["match_key"].lower()).strip("_") or "unknown"
    target = out_dir / f"match_{slug}.json"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(match, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def align(
    slates: list[dict[str, Any]],
    aliases: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    table = aliases if aliases is not None else {"teams": {}}
    table.setdefault("teams", {})
    clusters: list[dict[str, Any]] = []
    seen_indexes: set[str] = set()
    for slate in sorted(slates, key=_slate_sort_key):
        index = str(slate.get("index") or "")
        if index:
            seen_indexes.add(index)
        competition = str(slate.get("competition") or "")
        slate_date = str(slate.get("slate_date") or "")
        for row in slate.get("matches") or []:
            if not isinstance(row, dict):
                continue
            home = str(row.get("home") or "")
            away = str(row.get("away") or "")
            kickoff = str(row.get("kickoff") or "")
            if not home or not away or not kickoff:
                continue
            found = None
            for cluster in clusters:
                if _same_match(cluster, competition, slate_date, home, away, kickoff, table):
                    found = cluster
                    break
            if found is None:
                clusters.append(_new_cluster(index, competition, slate_date, home, away, kickoff, row))
            else:
                _attach(found, index, home, away, row, table)
    ordered = _ordered_indexes(seen_indexes)
    for cluster in clusters:
        for index in ordered:
            cluster["indexes"].setdefault(index, None)
    return clusters


def names_match(left: str, right: str, aliases: dict[str, Any] | None = None) -> bool:
    a = normalize_name(left)
    b = normalize_name(right)
    if not a or not b:
        return False
    if a == b:
        return True
    teams = (aliases or {}).get("teams") or {}
    ga = _group_key(teams, a)
    gb = _group_key(teams, b)
    if ga and gb and ga == gb:
        return True
    if ga and (b == ga or b in teams.get(ga, [])):
        return True
    if gb and (a == gb or a in teams.get(gb, [])):
        return True
    return SequenceMatcher(None, a, b).ratio() >= FUZZY_THRESHOLD


def _same_match(
    cluster: dict[str, Any],
    competition: str,
    slate_date: str,
    home: str,
    away: str,
    kickoff: str,
    aliases: dict[str, Any],
) -> bool:
    if competition_slug(cluster["competition"]) != competition_slug(competition):
        return False
    if cluster["slate_date"] != slate_date:
        return False
    if not _within_window(cluster["kickoff"], kickoff):
        return False
    return names_match(cluster["home"], home, aliases) and names_match(cluster["away"], away, aliases)


def _new_cluster(
    index: str,
    competition: str,
    slate_date: str,
    home: str,
    away: str,
    kickoff: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(row)
    score = payload.get("score", None)
    return {
        "contract": CONTRACT,
        "match_key": _match_key(competition, slate_date, kickoff, home, away),
        "competition": competition,
        "slate_date": slate_date,
        "home": home,
        "away": away,
        "kickoff": kickoff,
        "score": score,
        "indexes": {index: payload} if index else {},
    }


def _attach(
    cluster: dict[str, Any],
    index: str,
    home: str,
    away: str,
    row: dict[str, Any],
    aliases: dict[str, Any],
) -> None:
    if index and cluster["indexes"].get(index) is None:
        cluster["indexes"][index] = dict(row)
    if cluster.get("score") in (None, "") and row.get("score") not in (None, ""):
        cluster["score"] = row.get("score")
    _remember(aliases, cluster["home"], home)
    _remember(aliases, cluster["away"], away)


def _remember(aliases: dict[str, Any], left: str, right: str) -> None:
    a = normalize_name(left)
    b = normalize_name(right)
    if not a or not b or a == b:
        return
    teams: dict[str, list[str]] = aliases.setdefault("teams", {})
    ga = _group_key(teams, a)
    gb = _group_key(teams, b)
    if ga and gb:
        if ga != gb:
            _merge_groups(teams, ga, gb)
        return
    if ga:
        if b not in teams[ga] and b != ga:
            teams[ga].append(b)
        return
    if gb:
        if a not in teams[gb] and a != gb:
            teams[gb].append(a)
        return
    canon = a if len(a) <= len(b) else b
    other = b if canon == a else a
    teams[canon] = [other]


def _group_key(teams: dict[str, list[str]], name: str) -> str | None:
    if name in teams:
        return name
    for key, values in teams.items():
        if name in values:
            return key
    return None


def _merge_groups(teams: dict[str, list[str]], keep: str, drop: str) -> None:
    if keep == drop:
        return
    merged = list(teams.get(keep, []))
    if drop not in merged and drop != keep:
        merged.append(drop)
    for item in teams.get(drop, []):
        if item not in merged and item != keep:
            merged.append(item)
    teams[keep] = merged
    teams.pop(drop, None)


def _match_key(competition: str, slate_date: str, kickoff: str, home: str, away: str) -> str:
    hhmm = _parse_dt(kickoff).strftime("%H%M")
    return f"{competition_slug(competition)}:{slate_date}:{hhmm}:{name_slug(home)}:{name_slug(away)}"


def _within_window(left: str, right: str) -> bool:
    delta = abs((_parse_dt(left) - _parse_dt(right)).total_seconds())
    return delta <= WINDOW_MINUTES * 60


def _parse_dt(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _strip_accents(value: str) -> str:
    nfkd = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _slate_sort_key(slate: dict[str, Any]) -> tuple:
    index = str(slate.get("index") or "")
    try:
        order = INDEX_ORDER.index(index)
    except ValueError:
        order = len(INDEX_ORDER)
    return (order, index, str(slate.get("competition") or ""), str(slate.get("slate_date") or ""))


def _ordered_indexes(found: set[str]) -> list[str]:
    out = [name for name in INDEX_ORDER if name in found]
    out.extend(sorted(found.difference(INDEX_ORDER)))
    return out
