#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mnemos import export_csv, export_json, ingest, load_matches

FRIGATE = Path(__file__).resolve().parents[1]
REPO = FRIGATE.parent
IN_DIR = FRIGATE / "IN"
OUT_DIR = FRIGATE / "OUT"
SNAP_DIR = REPO / "ARCHIVUM" / "snapshots"
EXPORT_DIR = REPO / "ARCHIVUM" / "exports"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F02 — match JSON → snapshots + export")
    parser.add_argument("--in", dest="src", default=str(IN_DIR), help="dossier ou fichier match JSON")
    parser.add_argument("--out", default=str(OUT_DIR), help="dossier OUT")
    parser.add_argument("--snapshots", default=str(SNAP_DIR), help="dossier ARCHIVUM/snapshots")
    parser.add_argument("--exports", default=str(EXPORT_DIR), help="dossier ARCHIVUM/exports")
    parser.add_argument("--captured-at", required=True, help="horodatage ISO du poll")
    args = parser.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"missing in: {src}", file=sys.stderr)
        return 2
    matches = load_matches(src)
    store_dir = Path(args.snapshots)
    written = ingest(matches, args.captured_at, store_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in written:
        target = out_dir / path.name
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    export_dir = Path(args.exports)
    json_path = export_json(store_dir, export_dir / "snapshots.json", exported_at=args.captured_at)
    csv_path = export_csv(store_dir, export_dir / "snapshots.csv")
    lines = [str(p) for p in written] + [str(json_path), str(csv_path)]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
