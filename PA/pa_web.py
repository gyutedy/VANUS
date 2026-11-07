#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_app(root: Path | None = None):
    base = Path(root) if root is not None else ROOT
    cell_dir = base / "F05_CELL" / "CODEBASE"
    if not (cell_dir / "cell.py").is_file():
        cell_dir = ROOT / "F05_CELL" / "CODEBASE"
    if str(cell_dir) not in sys.path:
        sys.path.insert(0, str(cell_dir))
    from cell import load_store, route

    def application(environ, start_response):
        store = load_store(base / "F05_CELL" / "IN")
        path = environ.get("PATH_INFO") or "/"
        query = environ.get("QUERY_STRING") or ""
        status_code, body = route(store, path, query)
        label = "OK" if status_code == 200 else "Not Found" if status_code == 404 else "Error"
        payload = body.encode("utf-8")
        start_response(
            f"{status_code} {label}",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]

    return application


application = make_app()
