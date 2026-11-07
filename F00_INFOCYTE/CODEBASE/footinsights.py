from __future__ import annotations

import html as htmlmod
import json
import re
from datetime import datetime, timezone
from typing import Any

INDEX = "footinsights"
CONTRACT = "vanus.slate.v1"
USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_SOFT = re.compile("\u00ad")
_DAY = re.compile(
    r'<section\b[^>]*id="day-(\d{4}-\d{2}-\d{2})"[^>]*>([\s\S]*?)(?=<section\b[^>]*id="day-|\Z)',
    re.I,
)
_PGROUP = re.compile(
    r'<section\b([^>]*class="[^"]*\bpgroup\b[^"]*"[^>]*)>([\s\S]*?)</section>',
    re.I,
)
_LEAGUE_ATTR = re.compile(r'data-league="([^"]*)"', re.I)
_LEAGUE_H3 = re.compile(r'<h3\b[^>]*class="[^"]*\bn\b[^"]*"[^>]*>([\s\S]*?)</h3>', re.I)
_H3 = re.compile(r"<h3\b[^>]*>([\s\S]*?)</h3>", re.I)
_PROW_OPEN = re.compile(r'<a\b([^>]*)class="[^"]*\bprow\b[^"]*"([^>]*)>', re.I)
_HREF = re.compile(r'href="([^"]+)"', re.I)
_DATA_HOME = re.compile(r'data-home="([^"]+)"', re.I)
_DATA_AWAY = re.compile(r'data-away="([^"]+)"', re.I)
_DATA_DAY = re.compile(r'data-day="([^"]+)"', re.I)
_TIME = re.compile(r'<time\b[^>]*datetime="([^"]+)"', re.I)
_TN = re.compile(r'<span\b[^>]*class="[^"]*\btn\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_XT_CALL = re.compile(
    r'<span\b[^>]*class="[^"]*\bxt-call\b[^"]*"[^>]*>([\s\S]*?)</span>',
    re.I,
)
_XT_ODD = re.compile(r'<b\b[^>]*class="[^"]*\bxt-odd\b[^"]*"[^>]*>([\s\S]*?)</b>', re.I)
_X_SEL = re.compile(r'<span\b[^>]*class="[^"]*\bx-sel\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_X_ODD = re.compile(r'<b\b[^>]*class="[^"]*\bx-odd\b[^"]*"[^>]*>([\s\S]*?)</b>', re.I)
_XCELL = re.compile(
    r'<span\b[^>]*class="([^"]*\bxcell\b[^"]*)"[^>]*>',
    re.I,
)
_TRUST = re.compile(r"Trust\s+(\d+)\s*(?:out of\s+10|/10)?", re.I)
_PRED_SLUG = re.compile(
    r"/predictions/([a-z0-9-]+)-vs-([a-z0-9-]+)-(\d{4})-(\d{2})-(\d{2})",
    re.I,
)
_BLOG_HREF = re.compile(r'href="([^"]*/blog/([^"/?#]+)/?)"', re.I)
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_LOCKED = re.compile(r"\bis-lock\b|\blocked-call\b|Locked tip", re.I)
_UNLOCK = re.compile(
    r'<script\b[^>]*type="application/json"[^>]*data-unlock[^>]*>([\s\S]*?)</script>'
    r'|<script\b[^>]*data-unlock[^>]*type="application/json"[^>]*>([\s\S]*?)</script>',
    re.I,
)
_SKIP_BLOG = {"topic", "rss", "page"}
_SKIP_COMP = {"free picks", "free pick", "unknown"}
_LEAGUE_NAMES = {
    "premier-league": "Premier League",
    "la-liga": "La Liga",
    "serie-a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue-1": "Ligue 1",
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
    cap = captured_at or _now_utc()
    fallback = slate_date or _slate_date_from_html(html) or _today_utc()
    days = list(_DAY.finditer(html))
    chunks = [(m.group(1), m.group(2)) for m in days] if days else [(fallback, html)]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for section_date, body in chunks:
        for attrs, inner in _PGROUP.findall(body):
            comp = _competition(attrs, inner)
            if _norm(comp) in _SKIP_COMP:
                continue
            for row_attrs, row_inner in _prows(inner):
                parsed = _parse_prow(row_attrs, row_inner, section_date)
                if parsed is None:
                    continue
                day = parsed.pop("_slate_date", section_date)
                key = (day, comp)
                grouped.setdefault(key, [])
                if key not in order:
                    order.append(key)
                if not _dup(grouped[key], parsed):
                    grouped[key].append(parsed)
    return [_make_slate(comp, day, cap, grouped[(day, comp)], source_url) for day, comp in order]


def parse_blog_refs(html: str) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for _href, slug in _BLOG_HREF.findall(html):
        slug = slug.strip().strip("/").lower()
        if not slug or slug in _SKIP_BLOG:
            continue
        if slug in seen:
            continue
        seen.add(slug)
        refs.append(slug)
    return refs


def _today_body(html: str, slate_date: str) -> str:
    days = list(_DAY.finditer(html))
    if not days:
        return html
    for m in days:
        if m.group(1) == slate_date:
            return m.group(2)
    return ""


def _competition(attrs: str, inner: str) -> str:
    slug = (_first(_LEAGUE_ATTR, attrs) or "").strip()
    if slug:
        return _LEAGUE_NAMES.get(slug, _unslug(slug))
    name = _plain(_first(_LEAGUE_H3, inner) or "")
    if name:
        return name
    return _plain(_first(_H3, inner) or "") or "unknown"


def _prows(block: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _PROW_OPEN.finditer(block):
        attrs = m.group(1) + " " + m.group(2)
        start = m.end()
        close = block.lower().find("</a>", start)
        if close < 0:
            continue
        out.append((attrs, block[start:close]))
    return out


def _parse_prow(attrs: str, inner: str, slate_date: str) -> dict[str, Any] | None:
    href = _first(_HREF, attrs) or _first(_HREF, inner) or ""
    slug = _PRED_SLUG.search(href)
    day = _match_day(attrs, inner, slug, slate_date)
    home, away = _teams(attrs, inner, slug)
    if not home or not away:
        return None
    pick, model_pct, odds = _markets(inner)
    return {
        "home": home,
        "away": away,
        "kickoff": _kickoff(inner, slug, day),
        "score": None,
        "pick": pick,
        "model_pct": model_pct,
        "odds": odds,
        "raw_ref": _raw_ref(href, home, away),
        "_slate_date": day,
    }


def _match_day(attrs: str, inner: str, slug: re.Match[str] | None, fallback: str) -> str:
    if slug:
        return f"{slug.group(3)}-{slug.group(4)}-{slug.group(5)}"
    day = _first(_DATA_DAY, attrs)
    if day:
        return day
    raw = _first(_TIME, inner)
    if raw:
        stamp = _to_utc_z(raw)
        if len(stamp) >= 10 and stamp[4] == "-" and stamp[7] == "-":
            return stamp[:10]
    return fallback


def _teams(attrs: str, inner: str, slug: re.Match[str] | None) -> tuple[str, str]:
    home = _plain(_first(_DATA_HOME, attrs) or "")
    away = _plain(_first(_DATA_AWAY, attrs) or "")
    if home and away:
        return home, away
    names = [_plain(n) for n in _TN.findall(inner) if _plain(n)]
    if len(names) >= 2:
        return names[0], names[1]
    if slug:
        return _unslug(slug.group(1)), _unslug(slug.group(2))
    return "", ""


def _kickoff(inner: str, slug: re.Match[str] | None, slate_date: str) -> str:
    raw = _first(_TIME, inner)
    if raw:
        return _to_utc_z(raw)
    date = slate_date
    if slug:
        date = f"{slug.group(3)}-{slug.group(4)}-{slug.group(5)}"
    return f"{date}T00:00:00Z"


def _markets(inner: str) -> tuple[str | None, float | None, dict[str, Any]]:
    unlocked = _markets_from_unlock(inner)
    if unlocked is not None:
        return unlocked
    call = _plain(_first(_XT_CALL, inner) or "")
    locked = bool(_LOCKED.search(inner) or _LOCKED.search(call))
    pick = None if locked or not call else call
    model_pct = None
    trust = _TRUST.search(inner)
    if trust:
        model_pct = int(trust.group(1)) / 10.0
    odds: dict[str, Any] = {}
    if locked:
        return pick, model_pct, odds
    price = _float(_plain(_first(_XT_ODD, inner) or ""))
    if price is not None:
        odds["pick"] = price
    for m in _XCELL.finditer(inner):
        klass = m.group(1).lower()
        rest = inner[m.end():]
        nxt = re.search(r'<span\b[^>]*class="[^"]*\b(?:xcell|xtip-cell)\b', rest, re.I)
        body = rest[: nxt.start()] if nxt else rest
        sel = _plain(_first(_X_SEL, body) or "")
        odd = _float(_plain(_first(_X_ODD, body) or ""))
        if odd is None:
            continue
        if "goals" in klass:
            key = "over" if "over" in sel.lower() else "under"
            odds.setdefault("ou_25", {})[key] = odd
        elif "btts" in klass:
            key = "yes" if sel.lower() == "yes" else "no"
            odds.setdefault("btts", {})[key] = odd
    return pick, model_pct, odds


def _markets_from_unlock(inner: str) -> tuple[str | None, float | None, dict[str, Any]] | None:
    m = _UNLOCK.search(inner)
    if not m:
        return None
    raw = (m.group(1) or m.group(2) or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    tips = data.get("t") if isinstance(data, dict) else None
    if not isinstance(tips, list) or not tips:
        return None
    best = None
    for row in tips:
        if isinstance(row, list) and row and row[0] == "best":
            best = row
            break
    if best is None:
        best = next((row for row in tips if isinstance(row, list) and len(row) >= 5), None)
    if not isinstance(best, list) or len(best) < 5:
        return None
    market = str(best[1] or "")
    selection = str(best[2] or "")
    model_pct = best[3] if isinstance(best[3], (int, float)) else None
    price = best[4] if isinstance(best[4], (int, float)) else _float(str(best[4]) if best[4] is not None else None)
    pick = _unlock_pick(market, selection)
    odds: dict[str, Any] = {}
    if price is not None:
        odds["pick"] = float(price)
        _apply_unlock_market(odds, market, selection, float(price))
    return pick, float(model_pct) if isinstance(model_pct, (int, float)) else None, odds


def _unlock_pick(market: str, selection: str) -> str:
    market = market.lower()
    sel = selection.strip()
    mapping = {
        "home": "1",
        "draw": "X",
        "away": "2",
        "yes": "BTTS_YES",
        "no": "BTTS_NO",
    }
    if market in {"1x2", "result"}:
        return mapping.get(sel.lower(), sel)
    if market == "dc":
        return sel.upper()
    if market.startswith("ou"):
        line = market[2:]
        if line.isdigit() and len(line) == 2:
            line = f"{line[0]}.{line[1]}"
        return f"{sel.title()} {line}".strip()
    if market == "btts":
        return mapping.get(sel.lower(), sel)
    return sel or market


def _apply_unlock_market(odds: dict[str, Any], market: str, selection: str, price: float) -> None:
    market = market.lower()
    sel = selection.lower()
    if market in {"1x2", "result"}:
        side = {"home": "home", "draw": "draw", "away": "away"}.get(sel)
        if side:
            odds["1x2"] = {side: price}
    elif market.startswith("ou"):
        key = "over" if "over" in sel else "under"
        odds.setdefault("ou_25" if market in {"ou25", "ou_25"} else market, {})[key] = price
    elif market == "btts":
        odds.setdefault("btts", {})["yes" if sel == "yes" else "no"] = price


def _slate_date_from_html(html: str) -> str | None:
    m = re.search(
        r'<a\b[^>]*class="[^"]*\bdatepill selected\b[^"]*"[^>]*href="#day-(\d{4}-\d{2}-\d{2})"',
        html,
        re.I,
    )
    if m:
        return m.group(1)
    m = re.search(
        r'href="#day-(\d{4}-\d{2}-\d{2})"[^>]*class="[^"]*\bdatepill selected\b',
        html,
        re.I,
    )
    if m:
        return m.group(1)
    m = _PRED_SLUG.search(html)
    if m:
        return f"{m.group(3)}-{m.group(4)}-{m.group(5)}"
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


def _to_utc_z(value: str) -> str:
    raw = value.strip()
    if raw.endswith("Z"):
        return raw
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        iso = _ISO_DATE.search(raw)
        return f"{iso.group(1)}T00:00:00Z" if iso else raw
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
    text = _SOFT.sub("", fragment)
    text = htmlmod.unescape(_TAG.sub(" ", text))
    return _WS.sub(" ", text).strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(1) if m else None


def _slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
