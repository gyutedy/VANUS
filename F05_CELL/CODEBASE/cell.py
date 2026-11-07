from __future__ import annotations

import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

DEFAULT_MARKET = "1x2"
INDEX_ORDER = (
    "predictlix",
    "dailysportpick",
    "metapred",
    "footinsights",
    "besoccer",
)
INDEX_LABELS = {
    "predictlix": "PredictLix",
    "dailysportpick": "DailySportPick",
    "metapred": "MetaPred",
    "footinsights": "FootInsights",
    "besoccer": "BeSoccer",
    "pinnacle": "Pinnacle",
}
EMPTY = "pas trouve"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


class Store:
    def __init__(self) -> None:
        self.matches: dict[str, dict[str, Any]] = {}
        self.evolutions: dict[str, dict[str, Any]] = {}
        self.alerts: dict[str, dict[str, Any]] = {}

    def indexes(self) -> list[str]:
        found: set[str] = set()
        for match in self.matches.values():
            for name, payload in (match.get("indexes") or {}).items():
                if payload is not None:
                    found.add(str(name))
        return _ordered(found)

    def competitions(self, index: str) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for match in self._for_index(index):
            comp = str(match.get("competition") or "")
            if comp and comp not in seen:
                seen.add(comp)
                names.append(comp)
        return sorted(names, key=lambda c: c.lower())

    def matches_for(self, index: str, comp_slug: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for match in self._for_index(index):
            if comp_slug_of(str(match.get("competition") or "")) == comp_slug:
                out.append(match)
        return sorted(
            out,
            key=lambda m: (str(m.get("kickoff") or ""), str(m.get("home") or "")),
        )

    def _for_index(self, index: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for match in self.matches.values():
            payload = (match.get("indexes") or {}).get(index)
            if payload is not None:
                out.append(match)
        return out


def load_store(src: Path) -> Store:
    store = Store()
    files: list[Path] = []
    if src.is_file():
        files = [src]
    elif src.is_dir():
        files = sorted(src.glob("*.json"))
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        key = str(data.get("match_key") or "")
        contract = data.get("contract")
        if not key:
            continue
        if contract == "vanus.match.v1":
            store.matches[key] = data
        elif contract == "vanus.evolution.v1":
            store.evolutions[key] = data
        elif contract == "vanus.alert.v1":
            store.alerts[key] = data
    return store


def route(store: Store, path: str, query: str = "") -> tuple[int, str]:
    parsed = urlparse(path if "://" in path else f"http://cell{path}")
    raw = unquote(parsed.path)
    qs = parse_qs(parsed.query or query)
    market = (qs.get("market") or [DEFAULT_MARKET])[0] or DEFAULT_MARKET
    parts = [p for p in raw.strip("/").split("/") if p]
    if not parts:
        return 200, render_home(store)
    if parts[0] == "i" and len(parts) == 2:
        return 200, render_index(store, parts[1])
    if parts[0] == "i" and len(parts) == 4 and parts[2] == "c":
        return 200, render_competition(store, parts[1], parts[3])
    if parts[0] == "m" and len(parts) >= 2:
        key = "/".join(parts[1:])
        body = render_popup(store, key, market=market)
        if key not in store.matches:
            return 404, body
        return 200, body
    return 404, _page("CELL", "<p>pas trouve</p>")


def render_home(store: Store) -> str:
    items = store.indexes()
    if not items:
        body = "<h1>CELL</h1><p>pas trouve</p>"
        return _page("CELL", body)
    lis = "".join(
        f'<li><a href="/i/{html.escape(name, quote=True)}">{html.escape(label(name))}</a></li>'
        for name in items
    )
    body = f"<h1>CELL</h1><h2>Indexes</h2><ul>{lis}</ul>"
    return _page("CELL", body)


def render_index(store: Store, index: str) -> str:
    comps = store.competitions(index)
    title = label(index)
    nav = f'<p><a href="/">CELL</a> / {html.escape(title)}</p>'
    if not comps:
        return _page(title, nav + f"<h1>{html.escape(title)}</h1><p>pas trouve</p>")
    lis = "".join(
        f'<li><a href="/i/{html.escape(index, quote=True)}/c/{html.escape(comp_slug_of(c), quote=True)}">{html.escape(c)}</a></li>'
        for c in comps
    )
    body = nav + f"<h1>{html.escape(title)}</h1><h2>Competitions</h2><ul>{lis}</ul>"
    return _page(title, body)


def render_competition(store: Store, index: str, comp_slug: str) -> str:
    rows = store.matches_for(index, comp_slug)
    title = label(index)
    nav = (
        f'<p><a href="/">CELL</a> / '
        f'<a href="/i/{html.escape(index, quote=True)}">{html.escape(title)}</a></p>'
    )
    if not rows:
        return _page(title, nav + "<h1>Matchs</h1><p>pas trouve</p>")
    heading = html.escape(str(rows[0].get("competition") or comp_slug))
    lis = "".join(_match_li(m) for m in rows)
    body = nav + f"<h1>{heading}</h1><h2>Matchs</h2><ul>{lis}</ul>"
    return _page(f"{title} {heading}", body)


def render_popup(store: Store, match_key: str, market: str = DEFAULT_MARKET) -> str:
    match = store.matches.get(match_key)
    if match is None:
        return _page("CELL", "<h1>CELL</h1><p>pas trouve</p>")
    header = _header(match)
    banner = _banner(store.alerts.get(match_key))
    markets = _markets(match)
    if market not in markets:
        markets = [market] + markets
    mnav = _market_nav(match_key, markets, market)
    drawers = [_index_drawer(match, name, market) for name in _match_indexes(match)]
    drawers.append(_evolution_drawer(store.evolutions.get(match_key)))
    body = header + banner + mnav + "".join(drawers)
    return _page(_match_title(match), body)


def write_pages(store: Store, out_dir: Path, market: str = DEFAULT_MARKET) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    written.append(_write(out_dir / "index.html", render_home(store)))
    for index in store.indexes():
        written.append(_write(out_dir / f"index_{file_slug(index)}.html", render_index(store, index)))
        for comp in store.competitions(index):
            slug = comp_slug_of(comp)
            name = f"index_{file_slug(index)}_{file_slug(slug)}.html"
            written.append(_write(out_dir / name, render_competition(store, index, slug)))
    for key in store.matches:
        written.append(
            _write(out_dir / f"match_{file_slug(key)}.html", render_popup(store, key, market=market))
        )
    return written


def bind_server(store: Store, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    handler = type("BoundCellHandler", (CellHandler,), {"store": store})
    return ThreadingHTTPServer((host, port), handler)


def label(index: str) -> str:
    return INDEX_LABELS.get(index, index)


def comp_slug_of(value: str) -> str:
    return _NON_ALNUM.sub("", value.lower()) or "unknown"


def file_slug(value: str) -> str:
    return _NON_ALNUM.sub("_", value.lower()).strip("_") or "unknown"


class CellHandler(BaseHTTPRequestHandler):
    store: Store

    def do_GET(self) -> None:
        status, body = route(self.store, self.path)
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        self.send_error(405)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def _match_li(match: dict[str, Any]) -> str:
    key = str(match.get("match_key") or "")
    href = "/m/" + quote(key, safe="")
    line = f"{match.get('home') or ''} vs {match.get('away') or ''} · {match.get('kickoff') or ''}"
    return f'<li><a href="{html.escape(href, quote=True)}">{html.escape(line)}</a></li>'


def _header(match: dict[str, Any]) -> str:
    bits = [
        str(match.get("competition") or ""),
        f"{match.get('home') or ''} - {match.get('away') or ''}",
        str(match.get("kickoff") or ""),
    ]
    score = match.get("score")
    if score not in (None, ""):
        bits.append(str(score))
    text = " · ".join(b for b in bits if b)
    return (
        f'<p><a href="/">CELL</a></p>'
        f'<header class="head"><h1>{html.escape(text)}</h1></header>'
    )


def _banner(alert: dict[str, Any] | None) -> str:
    if not alert:
        return ""
    level = str(alert.get("level") or "")
    direction = str(alert.get("direction") or "")
    agreeing = ", ".join(str(x) for x in (alert.get("agreeing") or []))
    line = " — ".join(p for p in (level, direction, agreeing) if p)
    cls = "jackpot" if level == "jackpot" else "alarm"
    return f'<p class="banner {cls}">{html.escape(line)}</p>'


def _markets(match: dict[str, Any]) -> list[str]:
    found: set[str] = {DEFAULT_MARKET}
    for payload in (match.get("indexes") or {}).values():
        if not isinstance(payload, dict):
            continue
        odds = payload.get("odds")
        if isinstance(odds, dict):
            found.update(str(k) for k in odds.keys())
    ordered = [DEFAULT_MARKET]
    ordered.extend(sorted(k for k in found if k != DEFAULT_MARKET))
    return ordered


def _market_nav(match_key: str, markets: list[str], current: str) -> str:
    base = "/m/" + quote(match_key, safe="")
    parts: list[str] = []
    for name in markets:
        href = f"{base}?market={quote(name, safe='')}"
        label_txt = "1X2" if name.lower() == "1x2" else name
        if name == current:
            parts.append(f"<strong>{html.escape(label_txt)}</strong>")
        else:
            parts.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(label_txt)}</a>')
    return f'<p class="market">Marche : {" · ".join(parts)}</p>'


def _match_indexes(match: dict[str, Any]) -> list[str]:
    keys = {str(k) for k in (match.get("indexes") or {}).keys()}
    return _ordered(keys)


def _index_drawer(match: dict[str, Any], index: str, market: str) -> str:
    payload = (match.get("indexes") or {}).get(index)
    title = html.escape(label(index))
    if payload is None:
        inner = f"<p>{EMPTY}</p>"
    elif not isinstance(payload, dict):
        inner = f"<p>{EMPTY}</p>"
    else:
        inner = _fiche(payload, market)
    return f'<details class="drawer"><summary>{title}</summary>{inner}</details>'


def _fiche(payload: dict[str, Any], market: str) -> str:
    rows: list[str] = []
    pick = payload.get("pick")
    if pick not in (None, ""):
        rows.append(f"<p>pick : {html.escape(str(pick))}</p>")
    pct = payload.get("model_pct")
    if isinstance(pct, (int, float)):
        rows.append(f"<p>model_pct : {html.escape(str(pct))}</p>")
    odds = payload.get("odds")
    if isinstance(odds, dict):
        block = odds.get(market, odds.get(market.lower()))
        rows.append(_odds_block(block, market))
        ev = odds.get("ev")
        if ev not in (None, ""):
            rows.append(f"<p>ev : {html.escape(str(ev))}</p>")
    ref = payload.get("raw_ref")
    if ref not in (None, ""):
        rows.append(f"<p>raw_ref : {html.escape(str(ref))}</p>")
    if not rows:
        return f"<p>{EMPTY}</p>"
    return "".join(rows)


def _odds_block(block: Any, market: str) -> str:
    if isinstance(block, dict):
        items = "".join(
            f"<li>{html.escape(str(k))} : {html.escape(str(v))}</li>" for k, v in block.items()
        )
        return f"<p>{html.escape(market)}</p><ul>{items}</ul>"
    if isinstance(block, (int, float, str)):
        return f"<p>{html.escape(market)} : {html.escape(str(block))}</p>"
    return f"<p>{EMPTY}</p>"


def _evolution_drawer(evo: dict[str, Any] | None) -> str:
    title = "Evolution"
    if not evo or not evo.get("lines"):
        return f'<details class="drawer"><summary>{title}</summary><p>{EMPTY}</p></details>'
    lines = evo.get("lines") or []
    stamps: list[str] = []
    seen: set[str] = set()
    for line in lines:
        for point in line.get("points") or []:
            at = str(point.get("at") or "")
            if at and at not in seen:
                seen.add(at)
                stamps.append(at)
    stamps.sort()
    cols = [str(line.get("index") or "") for line in lines]
    head = "<th>at</th>" + "".join(f"<th>{html.escape(label(c))}</th>" for c in cols)
    body_rows: list[str] = []
    lookup: dict[tuple[str, str], Any] = {}
    for line in lines:
        name = str(line.get("index") or "")
        for point in line.get("points") or []:
            lookup[(name, str(point.get("at") or ""))] = point.get("odds")
    for at in stamps:
        cells = "".join(
            f"<td>{html.escape('' if lookup.get((c, at)) is None else str(lookup.get((c, at))))}</td>"
            for c in cols
        )
        body_rows.append(f"<tr><td>{html.escape(at)}</td>{cells}</tr>")
    table = f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    return f'<details class="drawer"><summary>{title}</summary>{table}</details>'


def _match_title(match: dict[str, Any]) -> str:
    return f"{match.get('home') or ''} vs {match.get('away') or ''}".strip() or "CELL"


def _ordered(names: set[str]) -> list[str]:
    out = [n for n in INDEX_ORDER if n in names]
    out.extend(sorted(names.difference(INDEX_ORDER)))
    return out


def _write(path: Path, body: str) -> Path:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)
    return path


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font:16px/1.45 sans-serif;max-width:52rem;margin:1.5rem auto;padding:0 1rem;color:#111}"
        "a{color:#123}"
        ".head{border-bottom:1px solid #ccc;padding-bottom:.5rem}"
        ".banner{padding:.5rem .75rem;border:1px solid #333}"
        ".banner.alarm{background:#f4e6c4}"
        ".banner.jackpot{background:#d4ead4}"
        "details.drawer{border:1px solid #bbb;margin:.5rem 0;padding:.4rem .6rem}"
        "summary{cursor:pointer;font-weight:600}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ccc;padding:.25rem .4rem;text-align:left}"
        "</style></head><body>"
        f"{body}"
        "<script>"
        "document.querySelectorAll('details.drawer').forEach(function(d){"
        "d.addEventListener('toggle',function(){"
        "if(d.open){document.querySelectorAll('details.drawer').forEach(function(o){"
        "if(o!==d){o.open=false;}});}"
        "});});"
        "</script></body></html>"
    )
