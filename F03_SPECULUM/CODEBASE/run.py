#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from speculum import (
    DEFAULT_MARKET,
    DEFAULT_SELECTION,
    assess,
    evolve,
    file_slug,
    load_seen,
    load_snapshots,
    save_seen,
    write_json,
)

FRIGATE = Path(__file__).resolve().parents[1]
IN_DIR = FRIGATE / "IN"
OUT_DIR = FRIGATE / "OUT"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F03 — snapshots → evolution + alertes")
    parser.add_argument("--in", dest="src", default=str(IN_DIR), help="dossier ou fichier snapshot JSON")
    parser.add_argument("--out", default=str(OUT_DIR), help="dossier OUT")
    parser.add_argument("--seen", default=None, help="fichier fingerprints deja emis")
    parser.add_argument("--market", default=DEFAULT_MARKET)
    parser.add_argument("--selection", default=DEFAULT_SELECTION)
    parser.add_argument(
        "--signal-out",
        default=str(FRIGATE.parent / "SHARED" / "OUT" / "signals"),
        help="export vanus.signal.v1 (vide pour desactiver)",
    )
    args = parser.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        print(f"missing in: {src}", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    seen_path = Path(args.seen) if args.seen else out_dir / "alert_seen.json"
    seen = load_seen(seen_path)
    written: list[Path] = []
    for snap in load_snapshots(src):
        evo = evolve(snap, market=args.market, selection=args.selection)
        slug = file_slug(str(evo.get("match_key") or ""))
        written.append(write_json(evo, out_dir / f"evolution_{slug}.json"))
        alert = assess(evo, seen)
        if alert is not None:
            written.append(write_json(alert, out_dir / f"alert_{slug}.json"))
    save_seen(seen, seen_path)
    if args.signal_out:
        import signals_export as _sigx

        snaps = load_snapshots(src)
        blob, _w = _sigx.aggregate(snaps, Path(args.signal_out))
        print(f"[SIGNAL] {len(blob['matches'])} match(s) -> {args.signal_out}")
    if written:
        print("\n".join(str(path) for path in written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
