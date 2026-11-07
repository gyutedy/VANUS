#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tariel import one_pass, run_loop

FRIGATE = Path(__file__).resolve().parents[1]
ROOT = FRIGATE.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TARIEL — orchestre F00…F05 via subprocess")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--once", action="store_true", help="une passe, pas de boucle")
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--poll-minutes", type=int, default=None)
    args = parser.parse_args(argv)

    root = Path(args.root)
    if args.once:
        result = one_pass(root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    done = run_loop(root, poll_minutes=args.poll_minutes, ticks=args.ticks)
    print(json.dumps({"ticks": len(done), "passes": done}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
