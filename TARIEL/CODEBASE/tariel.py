from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from gates import alerte_open, lecture_open, past_all_ko

DEFAULT_POLL = 120
FLOOR_POLL = 30
LECTURE_STEPS = (
    "F00_INFOCYTE",
    "F01_SCRYER",
    "F02_MNEMOS",
    "F03_SPECULUM",
    "F05_CELL",
)
ALERTE_STEPS = ("F04_CIPHER",)
RunFn = Callable[..., Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clamp_poll(minutes: int | None, floor: int = FLOOR_POLL, default: int = DEFAULT_POLL) -> int:
    value = default if minutes is None else int(minutes)
    return max(int(floor), value)


def load_poll(root: Path, override: int | None = None) -> int:
    path = root / "F00_INFOCYTE" / "IN" / "sources.json"
    minutes = DEFAULT_POLL
    floor = FLOOR_POLL
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        minutes = int(data.get("poll_minutes") or DEFAULT_POLL)
        floor = int(data.get("poll_floor_minutes") or FLOOR_POLL)
    if override is not None:
        minutes = int(override)
    return clamp_poll(minutes, floor=floor)


def load_kickoffs(root: Path) -> list[str]:
    folder = root / "F01_SCRYER" / "OUT"
    out: list[str] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("contract") == "vanus.match.v1":
            kickoff = data.get("kickoff")
            if kickoff:
                out.append(str(kickoff))
    return out


def default_commands(root: Path, now: str, python: str) -> dict[str, list[str]]:
    return {
        "F00_INFOCYTE": [
            python,
            str(root / "F00_INFOCYTE" / "CODEBASE" / "runner.py"),
            "--out",
            str(root / "F00_INFOCYTE" / "OUT"),
            "--delay",
            "0",
        ],
        "F01_SCRYER": [
            python,
            str(root / "F01_SCRYER" / "CODEBASE" / "run.py"),
            "--in",
            str(root / "F00_INFOCYTE" / "OUT"),
            "--out",
            str(root / "F01_SCRYER" / "OUT"),
        ],
        "F02_MNEMOS": [
            python,
            str(root / "F02_MNEMOS" / "CODEBASE" / "run.py"),
            "--in",
            str(root / "F01_SCRYER" / "OUT"),
            "--out",
            str(root / "F02_MNEMOS" / "OUT"),
            "--captured-at",
            now,
        ],
        "F03_SPECULUM": [
            python,
            str(root / "F03_SPECULUM" / "CODEBASE" / "run.py"),
            "--in",
            str(root / "F02_MNEMOS" / "OUT"),
            "--out",
            str(root / "F03_SPECULUM" / "OUT"),
            "--signal-out",
            str(root / "SHARED" / "OUT" / "signals"),
        ],
        "F05_CELL": [
            python,
            str(root / "F05_CELL" / "CODEBASE" / "run.py"),
            "--in",
            str(root / "F05_CELL" / "IN"),
            "--out",
            str(root / "F05_CELL" / "OUT"),
        ],
        "F04_CIPHER": [
            python,
            str(root / "F04_CIPHER" / "CODEBASE" / "run.py"),
            "--in",
            str(root / "F03_SPECULUM" / "OUT"),
            "--out",
            str(root / "F04_CIPHER" / "OUT"),
        ],
    }


def one_pass(
    root: Path,
    now: str | None = None,
    *,
    commands: dict[str, list[str]] | None = None,
    run: RunFn | None = None,
    python: str | None = None,
    lecture: bool = True,
    alerte: bool = True,
) -> dict[str, Any]:
    at = now or now_iso()
    py = python or sys.executable
    cmds = commands if commands is not None else default_commands(root, at, py)
    runner = run or _run
    _ensure_dirs(root)
    ran: list[dict[str, Any]] = []
    if lecture:
        for name in LECTURE_STEPS:
            if name == "F05_CELL":
                stage_cell_in(root)
            if name not in cmds:
                continue
            rc = _exec(cmds[name], runner)
            ran.append({"step": name, "gate": "lecture", "returncode": rc})
    if alerte:
        for name in ALERTE_STEPS:
            if name not in cmds:
                continue
            rc = _exec(cmds[name], runner)
            ran.append({"step": name, "gate": "alerte", "returncode": rc})
    return {"at": at, "ran": ran}


def run_loop(
    root: Path,
    *,
    now_fn: Callable[[], str] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    poll_minutes: int | None = None,
    ticks: int | None = None,
    commands: dict[str, list[str]] | None = None,
    run: RunFn | None = None,
    python: str | None = None,
) -> list[dict[str, Any]]:
    clock = now_fn or now_iso
    sleeper = sleep_fn or time.sleep
    wait = load_poll(root, poll_minutes)
    done: list[dict[str, Any]] = []
    while True:
        at = clock()
        kickoffs = load_kickoffs(root)
        lec = lecture_open(at, kickoffs)
        alr = alerte_open(at, kickoffs)
        if not lec and not alr:
            break
        done.append(
            one_pass(
                root,
                at,
                commands=commands,
                run=run,
                python=python,
                lecture=lec,
                alerte=alr,
            )
        )
        if ticks is not None and len(done) >= ticks:
            break
        if past_all_ko(at, load_kickoffs(root)):
            break
        sleeper(wait * 60)
    return done


def stage_cell_in(root: Path) -> None:
    dest = root / "F05_CELL" / "IN"
    dest.mkdir(parents=True, exist_ok=True)
    for folder in (root / "F01_SCRYER" / "OUT", root / "F03_SPECULUM" / "OUT"):
        if not folder.is_dir():
            continue
        for path in folder.glob("*.json"):
            (dest / path.name).write_bytes(path.read_bytes())


def _ensure_dirs(root: Path) -> None:
    for name in (
        "F00_INFOCYTE",
        "F01_SCRYER",
        "F02_MNEMOS",
        "F03_SPECULUM",
        "F04_CIPHER",
        "F05_CELL",
    ):
        (root / name / "IN").mkdir(parents=True, exist_ok=True)
        (root / name / "OUT").mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], **kwargs: Any) -> Any:
    return subprocess.run(cmd, check=False, **kwargs)


def _exec(cmd: list[str], runner: RunFn) -> int:
    proc = runner(cmd)
    if proc is None:
        return 0
    if isinstance(proc, int):
        return proc
    return int(getattr(proc, "returncode", 0) or 0)
