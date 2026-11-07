from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime, timezone
from typing import Any

INDEX = "metapred"
CONTRACT = "vanus.slate.v1"
USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_BLOCK = re.compile(
    r'<div\b[^>]*data-component="MatchListByLeague"[^>]*>([\s\S]*?)(?=<div\b[^>]*data-component=|$)',
    re.I,
)
_H2 = re.compile(r"<h2\b[^>]*>([\s\S]*?)</h2>", re.I)
_LEAGUE_HREF = re.compile(r'href="[^"]*/league/[^"]+"[^>]*>([\s\S]*?)</a>', re.I)
_TR = re.compile(r"<tr\b[^>]*>([\s\S]*?)</tr>", re.I)
_PRONOS = re.compile(r'href="([^"]*/pronostic/[^"]+)"', re.I)
_TEAM = re.compile(
    r'<span\b[^>]*class="[^"]*(?:team-name|font-serif text-sm font-semibold)[^"]*"[^>]*>([\s\S]*?)</span>',
    re.I,
)
_SLUG = re.compile(
    r"/pronostic/([a-z0-9-]+)-vs-([a-z0-9-]+)-(\d{2})-(\d{2})-(\d{4})",
    re.I,
)
_TIME = re.compile(r"\b(\d{1,2}:\d{2})\b")
_DAY_MON = re.compile(
    r"\b(\d{1,2})\s+(janv\.?|janvier|fevr\.?|févr\.?|fév\.?|mars|avr\.?|avril|mai|juin|juil\.?|juillet|aout|août|sept\.?|octobre|oct\.?|nov\.?|novembre|dec\.?|déc\.?|décembre)\b",
    re.I,
)
_ODD = re.compile(
    r'data-market="([^"]+)"[^>]*data-odd="([^"]+)"(?:[^>]*data-pct="([^"]+)")?',
    re.I,
)
_SCORE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
_MONTHS = {
    "janv": 1, "janvier": 1,
    "fevr": 2, "févr": 2, "fév": 2, "fevrier": 2, "février": 2,
    "mars": 3,
    "avr": 4, "avril": 4,
    "mai": 5,
    "juin": 6,
    "juil": 7, "juillet": 7,
    "aout": 8, "août": 8,
    "sept": 9, "septembre": 9,
    "oct": 10, "octobre": 10,
    "nov": 11, "novembre": 11,
    "dec": 12, "déc": 12, "décembre": 12, "decembre": 12,
}


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
    if competition:
        want = _norm(competition)
        for slate in slates:
            if _norm(slate["competition"]) == want:
                return slate
        return _empty(
            competition=competition.strip(),
            slate_date=slate_date or _slate_date_from_html(html) or _today_utc(),
            captured_at=captured_at or _now_utc(),
            source_url=source_url,
        )
    if slates:
        return slates[0]
    return _empty(
        competition="unknown",
        slate_date=slate_date or _slate_date_from_html(html) or _today_utc(),
        captured_at=captured_at or _now_utc(),
        source_url=source_url,
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
    blocks = _BLOCK.findall(html)
    if not blocks:
        blocks = [_strip_offday(html)]
    slates: list[dict[str, Any]] = []
    for block in blocks:
        if not block.strip():
            continue
        block = _strip_offday(block)
        comp = _competition(block)
        matches: list[dict[str, Any]] = []
        for row in _TR.findall(block):
            parsed = _parse_row(row, date)
            if parsed is None:
                continue
            if not _dup(matches, parsed):
                matches.append(parsed)
        if not matches and not comp:
            continue
        slates.append(_make_slate(comp or "unknown", date, cap, matches, source_url))
    return [s for s in slates if s["matches"] or s["competition"] != "unknown"]


def _strip_offday(html: str) -> str:
    html = re.sub(
        r'<div\b[^>]*data-component="(?:TomorrowList|YesterdayList|HierList|DemainList)"[^>]*>[\s\S]*$',
        "",
        html,
        flags=re.I,
    )
    return html


def _competition(block: str) -> str:
    href = _first(_LEAGUE_HREF, block)
    if href:
        return _plain(href)
    return _plain(_first(_H2, block) or "")


def _parse_row(row: str, slate_date: str) -> dict[str, Any] | None:
    href = _first(_PRONOS, row) or ""
    slug = _SLUG.search(href)
    home, away = _teams(row, slug)
    if not home or not away:
        return None
    kick_date = None
    if slug:
        kick_date = f"{slug.group(5)}-{slug.group(4)}-{slug.group(3)}"
        if kick_date != slate_date:
            return None
    clock = _first(_TIME, row) or "00:00"
    if len(clock) == 4:
        clock = "0" + clock
    kickoff = f"{kick_date or slate_date}T{clock}:00Z"
    odds, model_pct, pick = _markets(row)
    score = _score(row)
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


def _teams(row: str, slug: re.Match[str] | None) -> tuple[str, str]:
    names = [_plain(n) for n in _TEAM.findall(row)]
    names = [n for n in names if n and n.lower() != "vs"]
    if len(names) >= 2:
        return names[0], names[1]
    if slug:
        return _unslug(slug.group(1)), _unslug(slug.group(2))
    return "", ""


def _markets(row: str) -> tuple[dict[str, Any], float | None, str | None]:
    odds: dict[str, Any] = {}
    onex: dict[str, float] = {}
    pcts: dict[str, float] = {}
    for market, odd_s, pct_s in _ODD.findall(row):
        price = _float(odd_s)
        pct = _float(pct_s)
        if pct is not None and pct > 1:
            pct = pct / 100.0
        key = market.lower()
        if key.startswith("1x2-") and price is not None:
            side = key.split("-", 1)[1]
            onex[side] = price
            if pct is not None:
                pcts[side] = pct
        elif key.startswith("btts-") and price is not None:
            odds.setdefault("btts", {})[key.split("-", 1)[1]] = price
        elif key.startswith("ou25-") and price is not None:
            odds.setdefault("ou_25", {})[key.split("-", 1)[1]] = price
    if onex:
        odds["1x2"] = onex
    pick = None
    model_pct = None
    if pcts:
        side, model_pct = max(pcts.items(), key=lambda kv: kv[1])
        pick = {"home": "1", "draw": "X", "away": "2"}.get(side, side)
    return odds, model_pct, pick


def _score(row: str) -> str | None:
    text = _plain(row)
    m = _SCORE.search(text)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def _slate_date_from_html(html: str) -> str | None:
    m = _SLUG.search(html)
    if m:
        return f"{m.group(5)}-{m.group(4)}-{m.group(3)}"
    return None


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


def _empty(*, competition: str, slate_date: str, captured_at: str, source_url: str | None) -> dict[str, Any]:
    return _make_slate(competition, slate_date, captured_at, [], source_url)


def _dup(existing: list[dict[str, Any]], match: dict[str, Any]) -> bool:
    key = (match["home"], match["away"], match["kickoff"])
    return any((m["home"], m["away"], m["kickoff"]) == key for m in existing)


def _raw_ref(href: str, home: str, away: str) -> str:
    path = href.strip().strip("/")
    if path:
        slug = path.split("/")[-1]
        if slug:
            return slug
    return _slug(home) + "-vs-" + _slug(away)


def _unslug(text: str) -> str:
    return text.replace("-", " ").strip().title()


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
