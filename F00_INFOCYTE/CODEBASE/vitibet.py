from __future__ import annotations

import html as htmlmod
import re
from datetime import datetime, timezone
from typing import Any

INDEX = "vitibet"
CONTRACT = "vanus.slate.v1"
USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_TITLE = re.compile(r"class=['\"]league-title['\"]>([^<]+)</span>", re.I)
_ROW_OPEN = re.compile(r"<a\b([^>]*livescore-match-row[^>]*)>", re.I)
_TEAM = re.compile(r"class=['\"]livescore-team-name['\"]>([\s\S]*?)</span>", re.I)
_TIME = re.compile(r"data-time=['\"]([^'\"]+)['\"]", re.I)
_SCORE = re.compile(
    r"class=['\"]actual-score-row[^'\"]*['\"]>([\s\S]*?)</div>",
    re.I,
)
_TIP = re.compile(r"class=['\"]tip-indicator-circle['\"][^>]*>([\s\S]*?)</span>", re.I)
_PROB = re.compile(
    r"class=['\"]prob-head['\"]>([\s\S]*?)</div>\s*<div class=['\"]prob-val(?:\s+idx-val)?['\"]>([\s\S]*?)</div>",
    re.I,
)
_DATE_ATTR = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"', re.I)
_ISO_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_SCORE_NUM = re.compile(r"(\d+)\s*[–-]\s*(\d+)")


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
            if _norm(slate["competition"]) == want:
                return slate
        return _make_slate(competition.strip(), date, cap, [], source_url)
    if slates:
        return slates[0]
    return _make_slate("unknown", date, cap, [], source_url)


def parse_slates(
    html: str,
    *,
    slate_date: str | None = None,
    captured_at: str | None = None,
    source_url: str | None = None,
) -> list[dict[str, Any]]:
    date = slate_date or _slate_date_from_html(html) or _today_utc()
    cap = captured_at or _now_utc()
    titles = [(m.start(), _plain(m.group(1))) for m in _TITLE.finditer(html)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for m in _ROW_OPEN.finditer(html):
        attrs = m.group(1)
        close = html.lower().find("</a>", m.end())
        if close < 0:
            continue
        inner = html[m.end():close]
        parsed = _parse_row(attrs, inner, date)
        if parsed is None:
            continue
        comp = _competition_at(titles, m.start()) or "unknown"
        grouped.setdefault(comp, [])
        if comp not in order:
            order.append(comp)
        if not _dup(grouped[comp], parsed):
            grouped[comp].append(parsed)
    return [_make_slate(comp, date, cap, grouped[comp], source_url) for comp in order]


def _parse_row(attrs: str, inner: str, slate_date: str) -> dict[str, Any] | None:
    names = [_plain(n) for n in _TEAM.findall(inner) if _plain(n)]
    if len(names) < 2:
        return None
    home, away = names[0], names[1]
    kickoff = _kickoff(inner, slate_date)
    pick = _pick(inner)
    probs = _probs(inner)
    model_pct = _model_pct(pick, probs)
    return {
        "home": home,
        "away": away,
        "kickoff": kickoff,
        "score": _score(inner),
        "pick": pick,
        "model_pct": model_pct,
        "odds": _odds(probs),
        "raw_ref": _raw_ref(attrs, home, away),
    }


def _competition_at(titles: list[tuple[int, str]], pos: int) -> str | None:
    current = None
    for start, name in titles:
        if start > pos:
            break
        if name:
            current = name
    return current


def _kickoff(inner: str, slate_date: str) -> str:
    raw = _first(_TIME, inner)
    if raw:
        return _to_utc_z(raw)
    return f"{slate_date}T00:00:00Z"


def _pick(inner: str) -> str | None:
    text = _plain(_first(_TIP, inner) or "")
    if not text or text.lower() in {"n/a", "—", "-", "no data"}:
        return None
    return text


def _probs(inner: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for head, val in _PROB.findall(inner):
        label = _plain(head).upper()
        text = _plain(val)
        if not label or not text:
            continue
        if label == "INDEX":
            num = _float(text.replace("+", ""))
            if num is not None:
                out["index"] = num
            continue
        if text.endswith("%"):
            pct = _float(text[:-1])
            if pct is not None:
                out[label] = pct / 100.0
    return out


def _model_pct(pick: str | None, probs: dict[str, Any]) -> float | None:
    if not pick:
        return None
    token = pick.strip().upper().replace(" ", "")
    mapping = {"1": "1", "X": "X", "2": "2"}
    if token in mapping:
        val = probs.get(mapping[token])
        return float(val) if isinstance(val, (int, float)) else None
    parts = []
    for ch in token:
        if ch in {"1", "X", "2"} and ch in probs:
            parts.append(float(probs[ch]))
    if parts:
        return round(sum(parts), 4)
    return None


def _odds(probs: dict[str, Any]) -> dict[str, Any]:
    odds: dict[str, Any] = {}
    if "index" in probs:
        odds["index"] = probs["index"]
    return odds


def _score(inner: str) -> str | None:
    text = _plain(_first(_SCORE, inner) or "")
    m = _SCORE_NUM.search(text)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def _raw_ref(attrs: str, home: str, away: str) -> str:
    fid = re.search(r"data-fid=['\"]([^'\"]+)['\"]", attrs, re.I)
    if fid:
        return f"vitibet-{fid.group(1)}"
    href = re.search(r"href=['\"]([^'\"]+)['\"]", attrs, re.I)
    if href:
        return href.group(1).rstrip("/").split("/")[-1] or _slug(home) + "-vs-" + _slug(away)
    return _slug(home) + "-vs-" + _slug(away)


def _slate_date_from_html(html: str) -> str | None:
    m = _DATE_ATTR.search(html)
    if m:
        return m.group(1)
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


def _dup(existing: list[dict[str, Any]], match: dict[str, Any]) -> bool:
    key = (match["home"], match["away"], match["kickoff"])
    return any((m["home"], m["away"], m["kickoff"]) == key for m in existing)


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
