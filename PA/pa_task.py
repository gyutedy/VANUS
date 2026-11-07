#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PA scheduled task — un reveil TARIEL")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)
    code = root / "TARIEL" / "CODEBASE"
    if not (code / "tariel.py").is_file():
        code = ROOT / "TARIEL" / "CODEBASE"
    sys.path.insert(0, str(code))
    from tariel import now_iso, one_pass

    one_pass(root, now_iso())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
