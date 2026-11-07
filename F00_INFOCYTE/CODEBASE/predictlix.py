from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime, timezone
from typing import Any

INDEX = "predictlix"
CONTRACT = "vanus.slate.v1"
USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_ROW = re.compile(r'<tr\b[^>]*class="[^"]*\bmatch-row\b[^"]*"[^>]*>[\s\S]*?</tr>', re.I)
_TD = re.compile(r"<td\b([^>]*)>([\s\S]*?)</td>", re.I)
_CLASS = re.compile(r'\bclass="([^"]*)"', re.I)
_H1 = re.compile(r"<h1\b[^>]*>([\s\S]*?)</h1>", re.I)
_TIME_DT = re.compile(r'<time\b[^>]*datetime="([^"]+)"', re.I)
_HOME = re.compile(r'<span\b[^>]*class="[^"]*\bhome-team\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_AWAY = re.compile(r'<span\b[^>]*class="[^"]*\baway-team\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_HREF = re.compile(r'<a\b[^>]*class="[^"]*\bmatch-teams-link\b[^"]*"[^>]*href="([^"]+)"', re.I)
_HREF_ALT = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*class="[^"]*\bmatch-teams-link\b', re.I)
_ODDS_SLOT = re.compile(r'<span\b[^>]*class="[^"]*\boffer-odds-slot\b[^"]*"[^>]*>', re.I)
_ATTR = re.compile(r'data-offer-([a-z]+)="([^"]*)"', re.I)
_PROB = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_EV = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%")
_SCORE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
_TODAY = re.compile(r"Today\s*[-–]\s*(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2})", re.I)
_H3 = re.compile(r"<h3\b[^>]*>([\s\S]*?)</h3>", re.I)
_H2 = re.compile(r"<h2\b[^>]*>([\s\S]*?)</h2>", re.I)
_COUNTRY = re.compile(
    r'<span\b[^>]*class="[^"]*\bleague-country\b[^"]*"[^>]*>([\s\S]*?)</span>',
    re.I,
)


def parse_html(
    html: str,
    *,
    competition: str | None = None,
    slate_date: str | None = None,
    captured_at: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    slates = parse_slates(
        html,
        slate_date=slate_date,
        captured_at=captured_at,
        source_url=source_url,
    )
    date = slate_date or _slate_date_from_html(html) or _today_utc()
    cap = captured_at or _now_utc()
    if competition:
        want = _norm(competition)
        for slate in slates:
            got = _norm(slate["competition"])
            if got == want or want in got or got.endswith(want):
                return slate
        return _make_slate(competition.strip(), date, cap, [], source_url)
    if slates:
        return slates[0]
    text_h1 = _plain(_first(_H1, html) or "")
    return _make_slate(
        _competition_from_h1(text_h1) or "unknown",
        date,
        cap,
        [],
        source_url,
    )


def parse_slates(
    html: str,
    *,
    slate_date: str | None = None,
    captured_at: str | None = None,
    source_url: str | None = None,
) -> list[dict[str, Any]]:
    date = slate_date or _slate_date_from_html(html) or _today_utc()
    cap = captured_at or _now_utc()
    h2s = list(_H2.finditer(html))
    if h2s:
        slates: list[dict[str, Any]] = []
        for i, match in enumerate(h2s):
            name = _plain(match.group(1))
            if not name:
                continue
            end = h2s[i + 1].start() if i + 1 < len(h2s) else len(html)
            chunk = html[match.end():end]
            matches = _matches_from_html(chunk, date)
            if not matches:
                continue
            country = _plain(_first(_COUNTRY, chunk) or "")
            slates.append(_make_slate(_comp_label(name, country), date, cap, matches, source_url))
        return slates
    matches = _matches_from_html(html, date)
    text_h1 = _plain(_first(_H1, html) or "")
    comp = _competition_from_h1(text_h1) or "unknown"
    return [_make_slate(comp, date, cap, matches, source_url)]


def _matches_from_html(html: str, slate_date: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for row in _ROW.findall(html):
        parsed = _parse_row(row, slate_date)
        if parsed is not None:
            matches.append(parsed)
    return matches


def _make_slate(
    competition: str,
    slate_date: str,
    captured_at: str,
    matches: list[dict[str, Any]],
    source_url: str | None,
) -> dict[str, Any]:
    slate: dict[str, Any] = {
        "contract": CONTRACT,
        "index": INDEX,
        "competition": competition,
        "slate_date": slate_date,
        "captured_at": captured_at,
        "matches": matches,
    }
    if source_url:
        slate["source_url"] = source_url
    return slate


def _comp_label(name: str, country: str) -> str:
    if country and country.lower() not in name.lower():
        return f"{country} {name}"
    return name


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _parse_row(row: str, slate_date: str) -> dict[str, Any] | None:
    cells = _cells(row)
    home = _plain(_first(_HOME, row) or "")
    away = _plain(_first(_AWAY, row) or "")
    if not home or not away:
        return None
    kickoff = _kickoff(cells.get("time-cell", ""), slate_date)
    pick = _pick(cells.get("prediction-cell", ""))
    model_pct = _pct(_PROB, cells.get("prob-cell", ""))
    score = _score(cells.get("result-cell", ""))
    odds = _odds(cells.get("odds-cell", ""), cells.get("ev-cell", ""), pick)
    href = _first(_HREF, row) or _first(_HREF_ALT, row) or ""
    return {
        "home": home,
        "away": away,
        "kickoff": kickoff,
        "score": score,
        "pick": pick,
        "model_pct": model_pct,
        "odds": odds,
        "raw_ref": _raw_ref(href, home, away),
    }


def _cells(row: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for attrs, body in _TD.findall(row):
        cls = _CLASS.search(attrs)
        if not cls:
            continue
        names = cls.group(1).split()
        if names:
            out[names[0]] = body
    return out


def _kickoff(time_cell: str, slate_date: str) -> str:
    dt = _first(_TIME_DT, time_cell)
    if dt:
        return _to_utc_z(dt)
    clock = _plain(time_cell)
    if re.fullmatch(r"\d{1,2}:\d{2}", clock):
        return f"{slate_date}T{clock}:00Z"
    return f"{slate_date}T00:00:00Z"


def _pick(cell: str) -> str | None:
    text = _plain(cell)
    if not text or text.lower() in {"no data", "n/a", "—", "-"}:
        return None
    key = text.strip().lower()
    mapping = {
        "home": "1",
        "draw": "X",
        "away": "2",
        "1": "1",
        "x": "X",
        "2": "2",
        "btts: yes": "BTTS_YES",
        "btts yes": "BTTS_YES",
        "yes": "BTTS_YES",
        "btts: no": "BTTS_NO",
        "btts no": "BTTS_NO",
        "no": "BTTS_NO",
    }
    return mapping.get(key, text)


def _odds(odds_cell: str, ev_cell: str, pick: str | None) -> dict[str, Any]:
    odds: dict[str, Any] = {}
    slot = _ODDS_SLOT.search(odds_cell)
    attrs: dict[str, str] = {}
    if slot:
        attrs = {k.lower(): v for k, v in _ATTR.findall(slot.group(0))}
    price = _float(attrs.get("odd"))
    if price is None:
        price = _float(_plain(odds_cell))
    brand = attrs.get("brand")
    outcome = (attrs.get("outcome") or "").lower()
    market = (attrs.get("market") or "match_winner").lower()
    if price is not None:
        if market in {"match_winner", "1x2"}:
            bucket = "1x2"
            side = {"home": "home", "draw": "draw", "away": "away"}.get(outcome)
            if side is None and pick in {"1", "X", "2"}:
                side = {"1": "home", "X": "draw", "2": "away"}[pick]
            if side:
                odds[bucket] = {side: price}
            else:
                odds[bucket] = {"pick": price}
        else:
            odds[market] = {"pick": price}
        if brand:
            odds["book"] = brand
            if brand.strip().lower() == "pinnacle":
                pinnacle: dict[str, Any] = {"price": price}
                if outcome:
                    pinnacle["outcome"] = outcome
                odds["pinnacle"] = pinnacle
    ev = _pct(_EV, ev_cell)
    if ev is not None:
        odds["ev"] = ev
    return odds


def _score(cell: str) -> str | None:
    if "result-upcoming" in cell:
        return None
    m = _SCORE.search(_plain(cell))
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def _raw_ref(href: str, home: str, away: str) -> str:
    path = href.strip().strip("/")
    if path:
        slug = path.rstrip("/").split("/")[-1]
        if slug:
            return slug
    return _slug(home) + "-vs-" + _slug(away)


def _competition_from_h1(text: str) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"\s*(Predictions|Betting Tips|and)\s*", " ", text, flags=re.I)
    cleaned = _WS.sub(" ", cleaned).strip(" -")
    m = re.search(r"(?:Spain|England|France|Germany|Italy|Japan)\s+(.+)$", cleaned, re.I)
    if m:
        return m.group(1).strip()
    return cleaned or None


def _slate_date_from_html(html: str) -> str | None:
    h3 = _plain(_first(_H3, html) or "")
    m = _TODAY.search(h3)
    if not m:
        return None
    month_name, day = m.group(1), int(m.group(2))
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    month = months.get(month_name.lower())
    if not month:
        return None
    year = datetime.now(timezone.utc).year
    return f"{year:04d}-{month:02d}-{day:02d}"


def _to_utc_z(value: str) -> str:
    raw = value.strip()
    if raw.endswith("Z"):
        return raw
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pct(pattern: re.Pattern[str], cell: str) -> float | None:
    text = _plain(cell)
    if not text or text in {"—", "-", "N/A"}:
        return None
    m = pattern.search(text)
    if not m:
        return None
    return float(m.group(1)) / 100.0


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


def _plain(fragment: str) -> str:
    text = htmlmod.unescape(_TAG.sub(" ", fragment))
    return _WS.sub(" ", text).strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(1) if m else None


def _slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
