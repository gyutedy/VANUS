from __future__ import annotations

import html as htmlmod
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

INDEX = "besoccer"
CONTRACT = "vanus.slate.v1"
USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"
SKIP_ON = (406,)

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_LEAGUE = re.compile(
    r'<section\b([^>]*class="[^"]*\bbs-league\b[^"]*"[^>]*)>([\s\S]*?)</section>',
    re.I,
)
_COMP_ATTR = re.compile(r'data-competition="([^"]+)"', re.I)
_H2 = re.compile(r"<h2\b[^>]*>([\s\S]*?)</h2>", re.I)
_MATCH = re.compile(
    r'<article\b([^>]*class="[^"]*\bbs-match\b[^"]*"[^>]*)>([\s\S]*?)</article>',
    re.I,
)
_KICK_ATTR = re.compile(r'data-kickoff="([^"]+)"', re.I)
_HOME = re.compile(r'<span\b[^>]*class="[^"]*\bhome-name\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_AWAY = re.compile(r'<span\b[^>]*class="[^"]*\baway-name\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_HREF = re.compile(r'href="([^"]+)"', re.I)
_ODD = re.compile(
    r'data-market="([^"]+)"[^>]*data-odd="([^"]+)"|data-odd="([^"]+)"[^>]*data-market="([^"]+)"',
    re.I,
)
_SCORE = re.compile(r'<span\b[^>]*class="[^"]*\bscore\b[^"]*"[^>]*>([\s\S]*?)</span>', re.I)
_SCORE_NUM = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_H1 = re.compile(r"<h1\b[^>]*>([\s\S]*?)</h1>", re.I)
_EN_DATE = re.compile(
    r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
    re.I,
)
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
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
    slates: list[dict[str, Any]] = []
    for attrs, inner in _LEAGUE.findall(html):
        comp = _plain(_first(_COMP_ATTR, attrs) or "") or _plain(_first(_H2, inner) or "")
        if _norm(comp) in {"", "tomorrow", "yesterday", "hier", "demain"}:
            continue
        matches: list[dict[str, Any]] = []
        for mattrs, minner in _MATCH.findall(inner):
            parsed = _parse_match(mattrs, minner, date)
            if parsed is None:
                continue
            if not _dup(matches, parsed):
                matches.append(parsed)
        if matches:
            slates.append(_make_slate(comp, date, cap, matches, source_url))
    return slates


def fetch(
    url: str,
    *,
    urlopen: Callable | None = None,
    skip_on: tuple[int, ...] = SKIP_ON,
    log: Callable[[str], None] | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    logger = log or (lambda msg: print(msg, file=sys.stderr))
    opener = urlopen or urllib.request.urlopen
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        resp = opener(req, timeout=timeout)
        with resp:
            body = resp.read()
            if isinstance(body, bytes):
                html = body.decode("utf-8", errors="replace")
            else:
                html = str(body)
            status = int(getattr(resp, "status", None) or getattr(resp, "code", 200) or 200)
            return {"ok": True, "status": status, "skipped": False, "html": html, "url": url, "retries": 0}
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        if status in skip_on:
            logger(f"besoccer skip status={status} url={url} reason=not_acceptable")
        else:
            logger(f"besoccer skip status={status} url={url} reason=http_error")
        return {"ok": False, "status": status, "skipped": True, "html": None, "url": url, "retries": 0}
    except urllib.error.URLError:
        logger(f"besoccer skip status=0 url={url} reason=url_error")
        return {"ok": False, "status": 0, "skipped": True, "html": None, "url": url, "retries": 0}


def _parse_match(attrs: str, inner: str, slate_date: str) -> dict[str, Any] | None:
    kick_raw = _first(_KICK_ATTR, attrs) or _first(_KICK_ATTR, inner)
    kickoff = _to_utc_z(kick_raw) if kick_raw else f"{slate_date}T00:00:00Z"
    if not kickoff.startswith(slate_date):
        return None
    home = _plain(_first(_HOME, inner) or "")
    away = _plain(_first(_AWAY, inner) or "")
    if not home or not away:
        return None
    href = _first(_HREF, inner) or ""
    return {
        "home": home,
        "away": away,
        "kickoff": kickoff,
        "score": _score(inner),
        "pick": None,
        "model_pct": None,
        "odds": _odds(inner),
        "raw_ref": _raw_ref(href, home, away),
    }


def _odds(inner: str) -> dict[str, Any]:
    onex: dict[str, float] = {}
    for a, b, c, d in _ODD.findall(inner):
        market = (a or d).lower()
        price = _float(b or c)
        if price is None:
            continue
        if market.startswith("1x2-"):
            onex[market.split("-", 1)[1]] = price
    if onex:
        return {"1x2": onex}
    return {}


def _score(inner: str) -> str | None:
    text = _plain(_first(_SCORE, inner) or "")
    m = _SCORE_NUM.search(text)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def _slate_date_from_html(html: str) -> str | None:
    heading = _plain(_first(_H1, html) or "")
    m = _EN_DATE.search(heading)
    if m:
        month = _MONTHS.get(m.group(2).lower())
        if month:
            return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"
    m = _ISO_DATE.search(html)
    return m.group(1) if m else None


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
    return _slug(home) + "-" + _slug(away)


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
    text = htmlmod.unescape(_TAG.sub(" ", fragment))
    return _WS.sub(" ", text).strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(1) if m else None


def _slug(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")
