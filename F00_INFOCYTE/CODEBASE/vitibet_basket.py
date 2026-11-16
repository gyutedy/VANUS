from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime, timezone
from typing import Any

INDEX = "vitibet_basket"
CONTRACT = "vanus.slate.v1"
SPORT = "basket"
SOURCE_URL = "https://www.vitibet.com/index.php?clanek=quicktips&sekce=basket&lang=en"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_TITLE = re.compile(r"class=['\"]league-title['\"]>([^<]+)</span>", re.I)
_ROW_OPEN = re.compile(r"<a\b([^>]*livescore-match-row[^>]*)>", re.I)
_TEAM = re.compile(r"class=['\"]livescore-team-name['\"]>([\s\S]*?)</span>", re.I)
_TIME = re.compile(r"data-time=['\"]([^'\"]+)['\"]", re.I)
_TIP = re.compile(r"class=['\"]tip-indicator-circle['\"][^>]*>([\s\S]*?)</span>", re.I)
_PROB = re.compile(
    r"class=['\"]prob-head['\"]>([\s\S]*?)</div>\s*<div class=['\"]prob-val(?:\s+idx-val)?['\"]>([\s\S]*?)</div>",
    re.I,
)
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_BASKET_PICKS = {"1": "home", "2": "away", "home": "home", "away": "away"}


def parse_html(
    html: str,
    *,
    competition: str | None = None,
    slate_date: str | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    slates = parse_slates(html, slate_date=slate_date, captured_at=captured_at)
    date = slate_date or _date_from_html(html) or _today_utc()
    cap = captured_at or _now_utc()
    if competition:
        want = _norm(competition)
        for slate in slates:
            if _norm(slate["competition"]) == want:
                return slate
        return _make_slate(competition.strip(), date, cap, [], [])
    return slates[0] if slates else _make_slate("unknown", date, cap, [], [])


def parse_slates(
    html: str,
    *,
    slate_date: str | None = None,
    captured_at: str | None = None,
) -> list[dict[str, Any]]:
    date = slate_date or _date_from_html(html) or _today_utc()
    cap = captured_at or _now_utc()
    titles = [(m.start(), _plain(m.group(1))) for m in _TITLE.finditer(html)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for m in _ROW_OPEN.finditer(html):
        close = html.lower().find("</a>", m.end())
        if close < 0:
            continue
        row = _parse_row(m.group(1), html[m.end():close], date)
        if row is None:
            continue
        comp = _competition_at(titles, m.start()) or "unknown"
        grouped.setdefault(comp, [])
        if comp not in order:
            order.append(comp)
        if not _dup(grouped[comp], row):
            grouped[comp].append(row)
    return [_make_slate(comp, date, cap, grouped[comp], []) for comp in order]


def _parse_row(attrs: str, inner: str, slate_date: str) -> dict[str, Any] | None:
    names = [_plain(n) for n in _TEAM.findall(inner) if _plain(n)]
    if len(names) < 2:
        return None
    pick = _pick(inner)
    probs = _probs(inner)
    return {
        "home": names[0],
        "away": names[1],
        "kickoff": _kickoff(inner, slate_date),
        "pick": pick,
        "model_pct": _model_pct(pick, probs),
        "odds": _odds(probs),
        "raw_ref": _raw_ref(attrs),
    }


def _pick(inner: str) -> str | None:
    raw = _plain(_first(_TIP, inner) or "")
    if not raw or raw.lower() in {"n/a", "—", "-", "no data", "x"}:
        return None
    return _BASKET_PICKS.get(raw.strip().lower())


def _probs(inner: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for head, val in _PROB.findall(inner):
        label = _plain(head).upper()
        text = _plain(val)
        if not text.endswith("%"):
            continue
        pct = _float(text[:-1])
        if pct is None:
            continue
        if label in ("1", "HOME"):
            out["home_pct"] = pct / 100.0
        elif label in ("2", "AWAY"):
            out["away_pct"] = pct / 100.0
        elif label == "INDEX":
            out["index"] = _float(text.replace("%", ""))
    return out


def _model_pct(pick: str | None, probs: dict[str, Any]) -> float | None:
    if pick == "home":
        val = probs.get("home_pct")
        return float(val) if isinstance(val, (int, float)) else None
    if pick == "away":
        val = probs.get("away_pct")
        return float(val) if isinstance(val, (int, float)) else None
    return None


def _odds(probs: dict[str, Any]) -> dict[str, Any]:
    return {"p_home": probs.get("home_pct"), "p_away": probs.get("away_pct")}


def _kickoff(inner: str, slate_date: str) -> str:
    raw = _first(_TIME, inner)
    if raw:
        iso = _ISO_DATE.search(raw)
        day = iso.group(1) if iso else slate_date
        clock = raw.strip().split()[-1] if len(raw.strip().split()) > 1 else "00:00:00"
        return f"{day}T{clock}Z"
    return f"{slate_date}T00:00:00Z"


def _competition_at(titles: list[tuple[int, str]], pos: int) -> str | None:
    current = None
    for start, name in titles:
        if start > pos:
            break
        if name:
            current = name
    return current


def _date_from_html(html: str) -> str | None:
    m = _ISO_DATE.search(html)
    return m.group(1) if m else None


def _raw_ref(attrs: str) -> str:
    fid = re.search(r"data-fid=['\"]([^'\"]+)['\"]", attrs, re.I)
    return "vitibet-basket-" + fid.group(1) if fid else "vitibet-basket"


def _make_slate(competition: str, slate_date: str, captured_at: str,
                matches: list[dict[str, Any]], holes: list[str]) -> dict[str, Any]:
    return {
        "contract": CONTRACT,
        "index": INDEX,
        "sport": SPORT,
        "competition": competition,
        "slate_date": slate_date,
        "captured_at": captured_at,
        "source_url": SOURCE_URL,
        "matches": matches,
        "holes": holes,
    }


def _dup(existing: list[dict[str, Any]], match: dict[str, Any]) -> bool:
    key = (match["home"], match["away"], match["kickoff"])
    return any((m["home"], m["away"], m["kickoff"]) == key for m in existing)


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def _plain(fragment: str) -> str:
    text = htmlmod.unescape(_TAG.sub(" ", fragment))
    return _WS.sub(" ", text).strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(1) if m else None


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace(",", ".")
    if not text or text.upper() in {"N/A", "—", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
