from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from besoccer import SKIP_ON as BESOCCER_SKIP
from besoccer import USER_AGENT as BESOCCER_UA
from besoccer import parse_html as parse_bs
from besoccer import parse_slates as parse_bs_slates
from dailysportpick import parse_html as parse_dsp
from dailysportpick import parse_slates as parse_dsp_slates
from footinsights import parse_html as parse_fi
from footinsights import parse_slates as parse_fi_slates
from httpget import USER_AGENT as HTTP_UA
from httpget import fetch as fetch_http
from metapred import parse_html as parse_mp
from metapred import parse_slates as parse_mp_slates
from predictlix import parse_html as parse_plx
from predictlix import parse_slates as parse_plx_slates
from run import write_slate
from vitibet import parse_html as parse_vb
from vitibet import parse_slates as parse_vb_slates

FRIGATE = Path(__file__).resolve().parents[1]
IN_DIR = FRIGATE / "IN"
OUT_DIR = FRIGATE / "OUT"
SOURCES_PATH = IN_DIR / "sources.json"

PARSERS = {
    "predictlix": parse_plx,
    "dailysportpick": parse_dsp,
    "metapred": parse_mp,
    "footinsights": parse_fi,
    "besoccer": parse_bs,
    "vitibet": parse_vb,
}
MULTI = {
    "predictlix": parse_plx_slates,
    "dailysportpick": parse_dsp_slates,
    "metapred": parse_mp_slates,
    "footinsights": parse_fi_slates,
    "besoccer": parse_bs_slates,
    "vitibet": parse_vb_slates,
}
HOSTS = {
    "predictlix": "https://predictlix.com",
    "dailysportpick": "https://dailysportpick.com",
    "metapred": "https://metapred.com",
    "footinsights": "https://footinsights.com",
    "besoccer": "https://www.besoccer.com",
    "vitibet": "https://www.vitibet.com",
}


def load_sources(path: Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else SOURCES_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def enabled_indexes(sources: dict[str, Any]) -> list[dict[str, Any]]:
    return [ix for ix in sources.get("indexes", []) if ix.get("enabled")]


def competitions_for(sources: dict[str, Any], index_id: str) -> list[dict[str, Any]]:
    return [c for c in sources.get("competitions", []) if c.get("index") == index_id]


def source_url_for(sources: dict[str, Any], index_id: str) -> str:
    entries = source_entries_for(sources, index_id)
    return entries[0]["url"] if entries else HOSTS.get(index_id, "").rstrip("/") + "/"


def source_entries_for(sources: dict[str, Any], index_id: str) -> list[dict[str, Any]]:
    host = HOSTS.get(index_id, "").rstrip("/")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for comp in competitions_for(sources, index_id):
        path = comp.get("path") or "/"
        url = str(path) if str(path).startswith("http") else host + str(path)
        if url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "competition": comp.get("name"), "id": comp.get("id")})
    if not out:
        out.append({"url": host + "/", "competition": None, "id": None})
    return out


def skip_on_for(index: dict[str, Any]) -> tuple[int, ...]:
    raw = index.get("skip_on") or []
    codes = tuple(int(x) for x in raw)
    if index.get("id") == "besoccer" and not codes:
        return BESOCCER_SKIP
    return codes


def run_fleet(
    sources: dict[str, Any] | None = None,
    *,
    html_by_index: dict[str, str] | None = None,
    fetchers: dict[str, Callable[..., dict[str, Any]]] | None = None,
    out_dir: Path | None = None,
    delay: float | None = None,
    sleep: Callable[[float], None] | None = None,
    log: Callable[[str], None] | None = None,
    captured_at: str | None = None,
    slate_date: str | None = None,
) -> dict[str, Any]:
    src = sources if sources is not None else load_sources()
    out = Path(out_dir) if out_dir is not None else OUT_DIR
    logger = log or (lambda msg: print(msg, file=sys.stderr))
    sleeper = sleep or time.sleep
    wait = src.get("inter_site_seconds", 2) if delay is None else delay
    html_map = html_by_index or {}
    fetch_map = fetchers or {}
    written: list[str] = []
    skipped: list[dict[str, Any]] = []
    called: list[str] = []
    first = True
    for index in src.get("indexes", []):
        index_id = index["id"]
        if not index.get("enabled"):
            continue
        entries = source_entries_for(src, index_id)
        html_override = html_map.get(index_id)
        one_shot = html_override is not None
        jobs = entries[:1] if one_shot else entries
        for entry in jobs:
            if not first and wait:
                sleeper(float(wait))
            first = False
            if index_id not in called:
                called.append(index_id)
            url = entry["url"]
            html = html_override
            if html is None:
                result = _fetch_index(index, url, fetch_map, logger)
                if result.get("skipped") or not result.get("ok"):
                    skipped.append(
                        {
                            "index": index_id,
                            "status": result.get("status"),
                            "url": url,
                            "retries": result.get("retries", 0),
                        }
                    )
                    continue
                html = result.get("html") or ""
            written.extend(
                _write_index(
                    index_id,
                    html,
                    out,
                    source_url=url,
                    slate_date=slate_date,
                    captured_at=captured_at,
                    competition=None if one_shot else entry.get("competition"),
                )
            )
    return {"written": written, "skipped": skipped, "called": called}


def _fetch_index(
    index: dict[str, Any],
    url: str,
    fetch_map: dict[str, Callable[..., dict[str, Any]]],
    logger: Callable[[str], None],
) -> dict[str, Any]:
    index_id = index["id"]
    if index_id in fetch_map:
        return fetch_map[index_id](url)
    return fetch_http(url, index=index_id, skip_on=skip_on_for(index), log=logger)


def _write_index(
    index_id: str,
    html: str,
    out_dir: Path,
    *,
    source_url: str | None,
    slate_date: str | None,
    captured_at: str | None,
    competition: str | None = None,
) -> list[str]:
    parser = PARSERS[index_id]
    paths: list[str] = []
    extra: dict[str, Any] = {}
    if competition:
        extra["competition"] = competition
    if index_id in MULTI:
        slates = MULTI[index_id](
            html,
            slate_date=slate_date,
            captured_at=captured_at,
            source_url=source_url,
        )
        if not slates:
            slates = [
                parser(
                    html,
                    slate_date=slate_date,
                    captured_at=captured_at,
                    source_url=source_url,
                    **extra,
                )
            ]
        for slate in slates:
            paths.append(str(write_slate(slate, out_dir)))
        return paths
    slate = parser(
        html,
        slate_date=slate_date,
        captured_at=captured_at,
        source_url=source_url,
        **extra,
    )
    paths.append(str(write_slate(slate, out_dir)))
    return paths


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="F00 runner — indexes enabled → OUT slates")
    parser.add_argument("--sources", default=str(SOURCES_PATH))
    parser.add_argument("--out", default=str(OUT_DIR))
    parser.add_argument("--delay", type=float, default=None)
    args = parser.parse_args(argv)
    result = run_fleet(
        load_sources(Path(args.sources)),
        out_dir=Path(args.out),
        delay=args.delay,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


assert BESOCCER_UA.startswith("VANUS/")
assert HTTP_UA.startswith("VANUS/")
assert "Chrome" not in HTTP_UA and "Mozilla" not in HTTP_UA

if __name__ == "__main__":
    raise SystemExit(main())
