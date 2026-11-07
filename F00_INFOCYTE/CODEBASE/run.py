#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from besoccer import parse_html as parse_bs
from besoccer import parse_slates as parse_bs_slates
from dailysportpick import parse_html as parse_dsp
from dailysportpick import parse_slates as parse_dsp_slates
from footinsights import parse_html as parse_fi
from footinsights import parse_slates as parse_fi_slates
from metapred import parse_html as parse_mp
from metapred import parse_slates as parse_mp_slates
from predictlix import parse_html as parse_plx
from predictlix import parse_slates as parse_plx_slates
from vitibet import parse_html as parse_vb
from vitibet import parse_slates as parse_vb_slates

FRIGATE = Path(__file__).resolve().parents[1]
OUT_DIR = FRIGATE / "OUT"

PARSERS = {
    "predictlix": parse_plx,
    "dailysportpick": parse_dsp,
    "metapred": parse_mp,
    "footinsights": parse_fi,
    "besoccer": parse_bs,
    "vitibet": parse_vb,
}
MULTI = {
    "predictlix": parse_plx_slates,
    "dailysportpick": parse_dsp_slates,
    "metapred": parse_mp_slates,
    "footinsights": parse_fi_slates,
    "besoccer": parse_bs_slates,
    "vitibet": parse_vb_slates,
}


def load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_slate(slate: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"slate_{slate['index']}_{_file_slug(slate['competition'])}_{slate['slate_date']}.json"
    target = out_dir / name
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(slate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def _file_slug(text: str) -> str:
    import re

    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F00 — HTML local → schema_slate.json")
    parser.add_argument("--html", required=True, help="chemin vers une fixture HTML")
    parser.add_argument("--index", default=None, help="predictlix | dailysportpick | metapred | footinsights | besoccer | vitibet")
    parser.add_argument("--out", default=str(OUT_DIR), help="dossier OUT")
    parser.add_argument("--competition", default=None)
    parser.add_argument("--slate-date", default=None)
    parser.add_argument("--source-url", default=None)
    args = parser.parse_args(argv)

    html_path = Path(args.html)
    if not html_path.is_file():
        print(f"missing html: {html_path}", file=sys.stderr)
        return 2
    index = (args.index or _guess_index(html_path.name)).lower()
    if index not in PARSERS:
        print(f"unknown index: {index}", file=sys.stderr)
        return 2
    html = load_html(html_path)
    out_dir = Path(args.out)
    if index in MULTI and not args.competition:
        written = []
        for slate in MULTI[index](
            html,
            slate_date=args.slate_date,
            source_url=args.source_url,
        ):
            written.append(write_slate(slate, out_dir))
        if not written:
            empty = PARSERS[index](
                html,
                slate_date=args.slate_date,
                source_url=args.source_url,
            )
            written.append(write_slate(empty, out_dir))
        print("\n".join(str(p) for p in written))
        return 0
    slate = PARSERS[index](
        html,
        competition=args.competition,
        slate_date=args.slate_date,
        source_url=args.source_url,
    )
    target = write_slate(slate, out_dir)
    print(target)
    return 0


def _guess_index(name: str) -> str:
    lower = name.lower()
    if "dailysportpick" in lower or lower.startswith("dsp"):
        return "dailysportpick"
    if "metapred" in lower:
        return "metapred"
    if "footinsights" in lower:
        return "footinsights"
    if "besoccer" in lower:
        return "besoccer"
    if "vitibet" in lower:
        return "vitibet"
    return "predictlix"


if __name__ == "__main__":
    raise SystemExit(main())
