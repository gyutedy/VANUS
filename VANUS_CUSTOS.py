#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LIBER_PATH = REPO_ROOT / "liber_vanus.json"

REQUIRED = ("contract", "fleet", "status", "frigates", "runtime")


def load(path: Path | None = None) -> dict:
    target = Path(path) if path is not None else LIBER_PATH
    with target.open(encoding="utf-8") as handle:
        data = json.load(handle)
    _check(data)
    return data


def save(data: dict, path: Path | None = None) -> None:
    _check(data)
    target = Path(path) if path is not None else LIBER_PATH
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(target)


def set_status(status: str, path: Path | None = None) -> dict:
    data = load(path)
    data["status"] = status
    save(data, path)
    return data


def set_frigate(name: str, state: str, path: Path | None = None) -> dict:
    data = load(path)
    if name not in data["frigates"]:
        raise KeyError(name)
    data["frigates"][name] = state
    save(data, path)
    return data


def _check(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("liber must be an object")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ValueError("liber missing: " + ", ".join(missing))
    if data.get("contract") != "vanus.liber.v1":
        raise ValueError("bad contract")
    if not isinstance(data.get("frigates"), dict):
        raise ValueError("frigates must be an object")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("status", "show"):
        print(json.dumps(load(), indent=2, ensure_ascii=False))
        return 0
    if args[0] == "set-status" and len(args) == 2:
        set_status(args[1])
        return 0
    if args[0] == "set-frigate" and len(args) == 3:
        set_frigate(args[1], args[2])
        return 0
    print("usage: VANUS_CUSTOS.py [status|set-status STATUS|set-frigate NAME STATE]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
