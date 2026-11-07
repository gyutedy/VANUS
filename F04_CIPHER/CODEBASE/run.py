#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cipher import (
    credentials,
    deliver,
    load_alerts,
    load_seen,
    save_seen,
    write_json,
)

FRIGATE = Path(__file__).resolve().parents[1]
IN_DIR = FRIGATE / "IN"
OUT_DIR = FRIGATE / "OUT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F04 — schema_alert.json → Telegram")
    parser.add_argument("--in", dest="src", default=str(IN_DIR), help="dossier ou fichier alert JSON")
    parser.add_argument("--out", default=str(OUT_DIR), help="dossier OUT")
    parser.add_argument("--seen", default=None, help="fichier fingerprints deja emis")
    args = parser.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"missing in: {src}", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    seen_path = Path(args.seen) if args.seen else out_dir / "cipher_seen.json"
    seen = load_seen(seen_path)
    token, chat_id = credentials()
    receipts = deliver(load_alerts(src), token, chat_id, seen, log=sys.stderr)
    save_seen(seen, seen_path)
    if receipts:
        written = write_json({"sent": receipts}, out_dir / "cipher_sent.json")
        print(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
