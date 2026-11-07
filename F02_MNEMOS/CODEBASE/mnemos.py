from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INDEX_ORDER = (
    "predictlix",
    "dailysportpick",
    "metapred",
    "footinsights",
    "besoccer",
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def load_matches(src: Path) -> list[dict[str, Any]]:
    if src.is_file():
        data = json.loads(src.read_text(encoding="utf-8"))
        return [data] if _is_match(data) else []
    matches: list[dict[str, Any]] = []
    if not src.is_dir():
        return matches
    for path in sorted(src.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if _is_match(data):
            matches.append(data)
    return matches


def load_snapshots(store_dir: Path) -> list[dict[str, Any]]:
    if not store_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(store_dir.glob("snap_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("match_key"):
            out.append(data)
    return out


def ingest(
    matches: list[dict[str, Any]],
    captured_at: str,
    store_dir: Path,
) -> list[Path]:
    store_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for match in matches:
        snap = _ingest_one(match, captured_at, store_dir)
        if snap is not None:
            written.append(snap)
    return written


def export_json(store_dir: Path, dest: Path, exported_at: str | None = None) -> Path:
    snapshots = load_snapshots(store_dir)
    payload = {
        "exported_at": exported_at or _now_utc(),
        "snapshots": snapshots,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)
    return dest


def export_csv(store_dir: Path, dest: Path) -> Path:
    snapshots = load_snapshots(store_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "match_key",
                "competition",
                "slate_date",
                "home",
                "away",
                "kickoff",
                "index",
                "captured_at",
                "pick",
                "score",
                "market",
                "selection",
                "odds",
            ]
        )
        for snap in snapshots:
            for point in snap.get("points") or []:
                rows = flatten_odds(point.get("odds") or {})
                if not rows:
                    rows = [("", "", "")]
                for market, selection, price in rows:
                    writer.writerow(
                        [
                            snap.get("match_key", ""),
                            snap.get("competition", ""),
                            snap.get("slate_date", ""),
                            snap.get("home", ""),
                            snap.get("away", ""),
                            snap.get("kickoff", ""),
                            point.get("index", ""),
                            point.get("captured_at", ""),
                            _cell(point.get("pick")),
                            _cell(point.get("score")),
                            market,
                            selection,
                            _cell(price),
                        ]
                    )
    tmp.replace(dest)
    return dest


def load_export_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_export_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def flatten_odds(odds: dict[str, Any]) -> list[tuple[str, str, Any]]:
    rows: list[tuple[str, str, Any]] = []
    if not isinstance(odds, dict):
        return rows
    for market, value in odds.items():
        if isinstance(value, dict):
            for selection, price in value.items():
                rows.append((str(market), str(selection), price))
        else:
            rows.append((str(market), "", value))
    return rows


def snapshot_slug(match_key: str) -> str:
    return _NON_ALNUM.sub("_", match_key.lower()).strip("_") or "unknown"


def _ingest_one(match: dict[str, Any], captured_at: str, store_dir: Path) -> Path | None:
    key = str(match.get("match_key") or "")
    if not key:
        return None
    points = _points_from_match(match, captured_at)
    if not points:
        return None
    target = store_dir / f"snap_{snapshot_slug(key)}.json"
    snap = _load_or_new(target, match)
    by_id = {(p.get("captured_at"), p.get("index")): i for i, p in enumerate(snap["points"])}
    for point in points:
        ident = (point["captured_at"], point["index"])
        if ident in by_id:
            snap["points"][by_id[ident]] = point
        else:
            by_id[ident] = len(snap["points"])
            snap["points"].append(point)
    snap["points"] = sorted(snap["points"], key=_point_sort_key)
    _write_json(target, snap)
    return target


def _points_from_match(match: dict[str, Any], captured_at: str) -> list[dict[str, Any]]:
    indexes = match.get("indexes") or {}
    points: list[dict[str, Any]] = []
    for name in _ordered_indexes(indexes):
        payload = indexes.get(name)
        if not isinstance(payload, dict):
            continue
        at = str(payload.get("captured_at") or match.get("captured_at") or captured_at)
        point: dict[str, Any] = {
            "captured_at": at,
            "index": name,
            "pick": payload.get("pick"),
            "score": payload.get("score", match.get("score")),
            "odds": payload.get("odds") if isinstance(payload.get("odds"), dict) else {},
        }
        if "model_pct" in payload:
            point["model_pct"] = payload.get("model_pct")
        if "raw_ref" in payload:
            point["raw_ref"] = payload.get("raw_ref")
        points.append(point)
    return points


def _load_or_new(path: Path, match: dict[str, Any]) -> dict[str, Any]:
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("points"), list):
            return data
    return {
        "match_key": match["match_key"],
        "competition": match.get("competition", ""),
        "slate_date": match.get("slate_date", ""),
        "home": match.get("home", ""),
        "away": match.get("away", ""),
        "kickoff": match.get("kickoff", ""),
        "points": [],
    }


def _ordered_indexes(indexes: dict[str, Any]) -> list[str]:
    names = [n for n in INDEX_ORDER if n in indexes]
    names.extend(sorted(set(indexes) - set(INDEX_ORDER)))
    return names


def _point_sort_key(point: dict[str, Any]) -> tuple:
    index = str(point.get("index") or "")
    try:
        order = INDEX_ORDER.index(index)
    except ValueError:
        order = len(INDEX_ORDER)
    return (str(point.get("captured_at") or ""), order, index)


def _is_match(data: Any) -> bool:
    return isinstance(data, dict) and data.get("contract") == "vanus.match.v1"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
