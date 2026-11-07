from __future__ import annotations

import sys
import urllib.error
import urllib.request
from typing import Any, Callable

USER_AGENT = "VANUS/0.1 (+https://github.com/gyutedy/VANUS; read-only public pages)"


def fetch(
    url: str,
    *,
    index: str,
    urlopen: Callable | None = None,
    skip_on: tuple[int, ...] = (),
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
            logger(f"{index} skip status={status} url={url} reason=not_acceptable")
        else:
            logger(f"{index} skip status={status} url={url} reason=http_error")
        return {"ok": False, "status": status, "skipped": True, "html": None, "url": url, "retries": 0}
    except urllib.error.URLError:
        logger(f"{index} skip status=0 url={url} reason=url_error")
        return {"ok": False, "status": 0, "skipped": True, "html": None, "url": url, "retries": 0}
