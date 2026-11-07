#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cell import DEFAULT_MARKET, bind_server, load_store, write_pages

FRIGATE = Path(__file__).resolve().parents[1]
IN_DIR = FRIGATE / "IN"
OUT_DIR = FRIGATE / "OUT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F05 — OUT/ARCHIVUM JSON → preview HTML")
    parser.add_argument("--in", dest="src", default=str(IN_DIR), help="dossier JSON match/evolution/alert")
    parser.add_argument("--out", default=str(OUT_DIR), help="dossier OUT HTML")
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--serve", action="store_true", help="servir HTTP local (pas de fetch sortant)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"missing in: {src}", file=sys.stderr)
        return 2
    store = load_store(src)
    written = write_pages(store, Path(args.out), market=args.market)
    if written:
        print("\n".join(str(path) for path in written))
    if args.serve:
        httpd = bind_server(store, args.host, args.port)
        host, port = httpd.server_address
        print(f"cell http://{host}:{port}", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
