#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scryer import align, load_aliases, load_slates, save_aliases, write_match

FRIGATE = Path(__file__).resolve().parents[1]
REPO = FRIGATE.parent
IN_DIR = FRIGATE / "IN"
OUT_DIR = FRIGATE / "OUT"
ALIASES_PATH = REPO / "ARCHIVUM" / "aliases.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F01 — slates JSON → schema_match.json")
    parser.add_argument("--in", dest="src", default=str(IN_DIR), help="dossier ou fichier slate JSON")
    parser.add_argument("--out", default=str(OUT_DIR), help="dossier OUT")
    parser.add_argument("--aliases", default=str(ALIASES_PATH), help="chemin aliases.json")
    args = parser.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"missing in: {src}", file=sys.stderr)
        return 2
    slates = load_slates(src)
    aliases_path = Path(args.aliases)
    aliases = load_aliases(aliases_path)
    matches = align(slates, aliases)
    save_aliases(aliases, aliases_path)
    out_dir = Path(args.out)
    written = [write_match(match, out_dir) for match in matches]
    if written:
        print("\n".join(str(path) for path in written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
