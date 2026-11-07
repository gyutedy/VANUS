from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime, timezone
from typing import Any

INDEX = "dailysportpick"
CONTRACT = "vanus.slate.v1"
USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_OPEN_CARD = re.compile(
    r'<div\b[^>]*class="[^"]*\bbt-(?:tip|extra)-card\b[^"]*"[^>]*>',
    re.I,
)
_LEAGUE = re.compile(r'<span\b[^>]*class="[^"]*\bbt-league\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_TEAM = re.compile(r'<span\b[^>]*class="[^"]*\bbt-team-name\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_PICK = re.compile(r'<div\b[^>]*class="[^"]*\bbt-pick-value\b[^"]*"[^>]*>([\s\S]*?)</div>', re.I)
_KICK_ATTR = re.compile(r'data-(?:dsp-kickoff|utc)="([^"]+)"', re.I)
_ODDS_ATTR = re.compile(r'data-dsp-odds="([^"]+)"', re.I)
_PROB_ATTR = re.compile(r'data-dsp-prob="([^"]+)"', re.I)
_MARKET_ATTR = re.compile(r'data-dsp-pick="([^"]+)"', re.I)
_ANALYSIS = re.compile(r'href="([^"]*\/analysis\/[^"]+)"', re.I)
_EXTRA_MATCH = re.compile(
    r'<div\b[^>]*class="[^"]*\bbt-extra-match\b[^"]*"[^>]*>([\s\S]*?)</div>',
    re.I,
)
_H2 = re.compile(r"<h2\b[^>]*>([\s\S]*?)</h2>", re.I)
_FR_DATE = re.compile(
    r"(\d{1,2})\s+(janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre)\s+(\d{4})",
    re.I,
)
_EN_DATE = re.compile(
    r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
    re.I,
)
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_MONTHS = {
    "janvier": 1, "january": 1,
    "fevrier": 2, "février": 2, "february": 2,
    "mars": 3, "march": 3,
    "avril": 4, "april": 4,
    "mai": 5, "may": 5,
    "juin": 6, "june": 6,
    "juillet": 7, "july": 7,
    "aout": 8, "août": 8, "august": 8,
    "septembre": 9, "september": 9,
    "octobre": 10, "october": 10,
    "novembre": 11, "november": 11,
    "decembre": 12, "décembre": 12, "december": 12,
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
        want = _norm_comp(competition)
        for slate in slates:
            if _norm_comp(slate["competition"]) == want:
                return slate
        return _empty_slate(
            competition=_competition_label(competition),
            slate_date=slate_date or _slate_date_from_html(html) or _today_utc(),
            captured_at=captured_at or _now_utc(),
            source_url=source_url,
        )
    if slates:
        return slates[0]
    return _empty_slate(
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
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for card in _cards(html):
        match = _parse_card(card, date)
        if match is None:
            continue
        comp = match.pop("_competition")
        grouped.setdefault(comp, [])
        if comp not in order:
            order.append(comp)
        if not _dup(grouped[comp], match):
            grouped[comp].append(match)
    slates = []
    for comp in order:
        slates.append(
            _make_slate(comp, date, cap, grouped[comp], source_url)
        )
    return slates


def _cards(html: str) -> list[str]:
    out: list[str] = []
    for m in _OPEN_CARD.finditer(html):
        block = _match_div(html, m.start())
        if block:
            out.append(block)
    return out


def _match_div(html: str, start: int) -> str | None:
    depth = 0
    i = start
    n = len(html)
    lower = html.lower()
    while i < n:
        nxt = lower.find("<div", i)
        close = lower.find("</div", i)
        if close < 0:
            return None
        if nxt != -1 and nxt < close:
            endtag = html.find(">", nxt)
            if endtag < 0:
                return None
            if not html[nxt:endtag].rstrip().endswith("/"):
                depth += 1
            i = endtag + 1
            continue
        endtag = html.find(">", close)
        if endtag < 0:
            return None
        depth -= 1
        i = endtag + 1
        if depth == 0:
            return html[start:i]
    return None


def _parse_card(card: str, slate_date: str) -> dict[str, Any] | None:
    league = _plain(_first(_LEAGUE, card) or "")
    comp = _competition_label(league) if league else "unknown"
    home, away = _teams(card)
    if not home or not away:
        return None
    kick = _first(_KICK_ATTR, card)
    kickoff = _to_utc_z(kick) if kick else f"{slate_date}T00:00:00Z"
    pick = _pick(_plain(_first(_PICK, card) or ""))
    model_pct = _prob(_first(_PROB_ATTR, card))
    odds = _odds(card, pick)
    href = _first(_ANALYSIS, card) or ""
    return {
        "_competition": comp,
        "home": home,
        "away": away,
        "kickoff": kickoff,
        "score": None,
        "pick": pick,
        "model_pct": model_pct,
        "odds": odds,
        "raw_ref": _raw_ref(href, home, away),
    }


def _teams(card: str) -> tuple[str, str]:
    names = [_plain(n) for n in _TEAM.findall(card)]
    names = [n for n in names if n]
    if len(names) >= 2:
        return names[0], names[1]
    extra = _first(_EXTRA_MATCH, card)
    if extra:
        text = _plain(extra)
        parts = re.split(r"\bvs\b", text, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    return "", ""


def _pick(text: str) -> str | None:
    if not text or text.lower() in {"no data", "n/a", "—", "-", "none"}:
        return None
    return text


def _odds(card: str, pick: str | None) -> dict[str, Any]:
    odds: dict[str, Any] = {}
    price = _float(_first(_ODDS_ATTR, card))
    market = _first(_MARKET_ATTR, card) or pick
    if price is None:
        return odds
    odds["pick"] = price
    if market:
        odds["market"] = market
    return odds


def _prob(raw: str | None) -> float | None:
    value = _float(raw)
    if value is None:
        return None
    if value > 1.0:
        return value / 100.0
    return value


def _competition_label(text: str) -> str:
    cleaned = _plain(text)
    if "," in cleaned:
        return cleaned.split(",")[-1].strip() or cleaned
    return cleaned or "unknown"


def _norm_comp(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def _slate_date_from_html(html: str) -> str | None:
    heading = _plain(_first(_H2, html) or "")
    m = _FR_DATE.search(heading) or _EN_DATE.search(heading)
    if m:
        day = int(m.group(1))
        month = _MONTHS.get(m.group(2).lower())
        year = int(m.group(3))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"
    kick = _first(_KICK_ATTR, html)
    if kick:
        iso = _ISO_DATE.search(kick)
        if iso:
            return iso.group(1)
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


def _empty_slate(
    *,
    competition: str,
    slate_date: str,
    captured_at: str,
    source_url: str | None,
) -> dict[str, Any]:
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
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
