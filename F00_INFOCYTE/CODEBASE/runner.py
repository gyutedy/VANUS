from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from besoccer import SKIP_ON as BESOCCER_SKIP
from besoccer import USER_AGENT as BESOCCER_UA
from besoccer import fetch as fetch_besoccer
from besoccer import parse_html as parse_bs
from besoccer import parse_slates as parse_bs_slates
from dailysportpick import parse_html as parse_dsp
from dailysportpick import parse_slates as parse_dsp_slates
from footinsights import parse_html as parse_fi
from footinsights import parse_slates as parse_fi_slates
from metapred import parse_html as parse_mp
from metapred import parse_slates as parse_mp_slates
from predictlix import parse_html as parse_plx
from run import write_slate

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
}
MULTI = {
    "dailysportpick": parse_dsp_slates,
    "metapred": parse_mp_slates,
    "footinsights": parse_fi_slates,
    "besoccer": parse_bs_slates,
}
HOSTS = {
    "predictlix": "https://predictlix.com",
    "dailysportpick": "https://dailysportpick.com",
    "metapred": "https://metapred.com",
    "footinsights": "https://footinsights.com",
    "besoccer": "https://www.besoccer.com",
}


def load_sources(path: Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else SOURCES_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def enabled_indexes(sources: dict[str, Any]) -> list[dict[str, Any]]:
    return [ix for ix in sources.get("indexes", []) if ix.get("enabled")]


def competitions_for(sources: dict[str, Any], index_id: str) -> list[dict[str, Any]]:
    return [c for c in sources.get("competitions", []) if c.get("index") == index_id]


def source_url_for(sources: dict[str, Any], index_id: str) -> str:
    comps = competitions_for(sources, index_id)
    host = HOSTS.get(index_id, "").rstrip("/")
    if comps:
        path = comps[0].get("path") or "/"
        if str(path).startswith("http"):
            return str(path)
        return host + str(path)
    return host + "/"


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
        if not first and wait:
            sleeper(float(wait))
        first = False
        called.append(index_id)
        url = source_url_for(src, index_id)
        html = html_map.get(index_id)
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
    if index_id == "besoccer":
        return fetch_besoccer(url, skip_on=skip_on_for(index), log=logger)
    logger(f"{index_id} skip status=0 url={url} reason=no_fetcher")
    return {"ok": False, "status": 0, "skipped": True, "html": None, "url": url, "retries": 0}


def _write_index(
    index_id: str,
    html: str,
    out_dir: Path,
    *,
    source_url: str | None,
    slate_date: str | None,
    captured_at: str | None,
) -> list[str]:
    parser = PARSERS[index_id]
    paths: list[str] = []
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

if __name__ == "__main__":
    raise SystemExit(main())
