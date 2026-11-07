from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EVO_CONTRACT = "vanus.evolution.v1"
ALERT_CONTRACT = "vanus.alert.v1"
DEFAULT_MARKET = "1x2"
DEFAULT_SELECTION = "home"
INDEX_ORDER = (
    "predictlix",
    "dailysportpick",
    "metapred",
    "footinsights",
    "besoccer",
    "vitibet",
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def load_snapshots(src: Path) -> list[dict[str, Any]]:
    if src.is_file():
        data = json.loads(src.read_text(encoding="utf-8"))
        return [data] if _is_snap(data) else []
    out: list[dict[str, Any]] = []
    if not src.is_dir():
        return out
    for path in sorted(src.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if _is_snap(data):
            out.append(data)
    return out


def load_seen(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {str(x) for x in raw}
    if isinstance(raw, dict) and isinstance(raw.get("fingerprints"), list):
        return {str(x) for x in raw["fingerprints"]}
    return set()


def save_seen(seen: set[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprints": sorted(seen)}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def evolve(
    snapshot: dict[str, Any],
    market: str = DEFAULT_MARKET,
    selection: str = DEFAULT_SELECTION,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    pinnacle_pts: list[dict[str, Any]] = []
    for point in snapshot.get("points") or []:
        if not isinstance(point, dict):
            continue
        index = str(point.get("index") or "")
        at = str(point.get("captured_at") or "")
        if not index or not at:
            continue
        price = _market_odds(point.get("odds") or {}, market, selection)
        grouped.setdefault(index, []).append({"at": at, "odds": price})
        pin = _pinnacle_price(point.get("odds") or {})
        if pin is not None:
            pinnacle_pts.append({"at": at, "odds": pin})
    lines: list[dict[str, Any]] = []
    for index in _ordered_indexes(grouped):
        pts = sorted(grouped[index], key=lambda p: p["at"])
        lines.append({"index": index, "role": "index", "points": pts})
    if pinnacle_pts:
        merged = _merge_at(pinnacle_pts)
        lines.append({"index": "pinnacle", "role": "pinnacle_ref", "points": merged})
    return {
        "contract": EVO_CONTRACT,
        "match_key": str(snapshot.get("match_key") or ""),
        "market": market,
        "selection": selection,
        "lines": lines,
    }


def assess(
    evolution: dict[str, Any],
    seen: set[str] | None = None,
) -> dict[str, Any] | None:
    known = seen if seen is not None else set()
    found: list[str] = []
    directions: dict[str, str] = {}
    last_at = ""
    pin_dir = None
    for line in evolution.get("lines") or []:
        role = line.get("role") or "index"
        index = str(line.get("index") or "")
        series = [p for p in (line.get("points") or []) if p.get("odds") is not None]
        if role == "pinnacle_ref":
            pin_dir = _direction(series)
            continue
        if not series:
            continue
        found.append(index)
        d = _direction(series)
        if d:
            directions[index] = d
        if series[-1]["at"] > last_at:
            last_at = series[-1]["at"]
    if len(found) < 2:
        return None
    shortening = [i for i, d in directions.items() if d == "shortening"]
    drifting = [i for i, d in directions.items() if d == "drifting"]
    if len(shortening) >= 2 and len(shortening) >= len(drifting):
        agreeing, direction = shortening, "shortening"
    elif len(drifting) >= 2:
        agreeing, direction = drifting, "drifting"
    else:
        return None
    agreeing = _ordered_indexes({n: None for n in agreeing})
    found = _ordered_indexes({n: None for n in found})
    level = "jackpot" if set(agreeing) == set(found) else "alarm"
    pin_agrees: bool | None
    if pin_dir is None:
        pin_agrees = None
    else:
        pin_agrees = pin_dir == direction
    fp = _fingerprint(
        str(evolution.get("match_key") or ""),
        str(evolution.get("market") or DEFAULT_MARKET),
        str(evolution.get("selection") or DEFAULT_SELECTION),
        direction,
        agreeing,
    )
    if fp in known:
        return None
    known.add(fp)
    alert = {
        "contract": ALERT_CONTRACT,
        "match_key": evolution.get("match_key"),
        "level": level,
        "market": evolution.get("market"),
        "selection": evolution.get("selection"),
        "direction": direction,
        "agreeing": agreeing,
        "found": found,
        "pinnacle_agrees": pin_agrees,
        "fingerprint": fp,
        "at": last_at,
    }
    return alert


def write_json(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def file_slug(match_key: str) -> str:
    return _NON_ALNUM.sub("_", match_key.lower()).strip("_") or "unknown"


def _fingerprint(match_key: str, market: str, selection: str, direction: str, agreeing: list[str]) -> str:
    joined = "+".join(agreeing)
    return f"{match_key}:{market}:{selection}:{direction}:{joined}"


def _direction(series: list[dict[str, Any]]) -> str | None:
    if len(series) < 2:
        return None
    first = series[0]["odds"]
    last = series[-1]["odds"]
    if first is None or last is None:
        return None
    if last < first:
        return "shortening"
    if last > first:
        return "drifting"
    return None


def _market_odds(odds: dict[str, Any], market: str, selection: str) -> float | None:
    if not isinstance(odds, dict):
        return None
    block = odds.get(market)
    if isinstance(block, dict):
        val = block.get(selection)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _pinnacle_price(odds: dict[str, Any]) -> float | None:
    if not isinstance(odds, dict):
        return None
    pin = odds.get("pinnacle")
    if isinstance(pin, (int, float)):
        return float(pin)
    if isinstance(pin, dict):
        for key in ("price", "home", "odds"):
            val = pin.get(key)
            if isinstance(val, (int, float)):
                return float(val)
    return None


def _merge_at(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_at: dict[str, float | None] = {}
    for point in points:
        by_at[point["at"]] = point["odds"]
    return [{"at": at, "odds": by_at[at]} for at in sorted(by_at)]


def _ordered_indexes(names: dict[str, Any] | set[str]) -> list[str]:
    keys = set(names)
    out = [n for n in INDEX_ORDER if n in keys]
    out.extend(sorted(keys.difference(INDEX_ORDER)))
    return out


def _is_snap(data: Any) -> bool:
    return isinstance(data, dict) and bool(data.get("match_key")) and isinstance(data.get("points"), list)
