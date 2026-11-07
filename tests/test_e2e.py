from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
HTML_DIR = REPO / "tests" / "fixtures" / "html"
HTMLS = (
    ("predictlix", "predictlix_la_liga.html"),
    ("dailysportpick", "dailysportpick_today.html"),
    ("metapred", "metapred_today.html"),
    ("footinsights", "footinsights_today.html"),
    ("besoccer", "besoccer_today.html"),
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run(codebase: Path, args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = {k: v for k, v in __import__("os").environ.items()}
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(codebase / "run.py"), *args],
        cwd=str(codebase),
        capture_output=True,
        text=True,
        check=True,
        env=merged,
    )


def _jsons(folder: Path) -> list[dict]:
    out: list[dict] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _prepare_two_index_odds(matches_dir: Path, home_odds: float) -> None:
    for path in sorted(matches_dir.glob("match_*.json")):
        match = json.loads(path.read_text(encoding="utf-8"))
        if match.get("contract") != "vanus.match.v1":
            continue
        indexes = match.setdefault("indexes", {})
        seed = None
        for payload in indexes.values():
            if isinstance(payload, dict):
                seed = dict(payload)
                break
        if seed is None:
            seed = {
                "home": match.get("home"),
                "away": match.get("away"),
                "kickoff": match.get("kickoff"),
            }
        for name in ("predictlix", "metapred"):
            row = dict(indexes.get(name) or seed)
            odds = dict(row.get("odds") or {})
            block = dict(odds.get("1x2") or {})
            block["home"] = home_odds
            block.setdefault("draw", 3.4)
            block.setdefault("away", 4.2)
            odds["1x2"] = block
            row["odds"] = odds
            indexes[name] = row
        _write(path, match)
        return


def test_e2e_html_to_cell_and_cipher(tmp_path):
    f00_out = tmp_path / "F00" / "OUT"
    f01_out = tmp_path / "F01" / "OUT"
    f02_out = tmp_path / "F02" / "OUT"
    f03_out = tmp_path / "F03" / "OUT"
    f04_out = tmp_path / "F04" / "OUT"
    f05_in = tmp_path / "F05" / "IN"
    f05_out = tmp_path / "F05" / "OUT"
    snaps = tmp_path / "ARCHIVUM" / "snapshots"
    exports = tmp_path / "ARCHIVUM" / "exports"
    aliases = tmp_path / "ARCHIVUM" / "aliases.json"
    for folder in (f00_out, f01_out, f02_out, f03_out, f04_out, f05_in, f05_out, snaps, exports):
        folder.mkdir(parents=True, exist_ok=True)

    for index, name in HTMLS:
        _run(
            REPO / "F00_INFOCYTE" / "CODEBASE",
            [
                "--html",
                str(HTML_DIR / name),
                "--index",
                index,
                "--out",
                str(f00_out),
                "--slate-date",
                "2026-11-07",
            ],
        )
    slates = [d for d in _jsons(f00_out) if d.get("contract") == "vanus.slate.v1"]
    assert slates
    for slate in slates:
        validate_instance(slate, "schema_slate.json")
    assert {s["index"] for s in slates} >= {"predictlix", "dailysportpick", "metapred"}

    _run(
        REPO / "F01_SCRYER" / "CODEBASE",
        ["--in", str(f00_out), "--out", str(f01_out), "--aliases", str(aliases)],
    )
    matches = [d for d in _jsons(f01_out) if d.get("contract") == "vanus.match.v1"]
    assert matches
    for match in matches:
        validate_instance(match, "schema_match.json")

    _prepare_two_index_odds(f01_out, 1.90)
    _run(
        REPO / "F02_MNEMOS" / "CODEBASE",
        [
            "--in",
            str(f01_out),
            "--out",
            str(f02_out),
            "--snapshots",
            str(snaps),
            "--exports",
            str(exports),
            "--captured-at",
            "2026-11-07T10:00:00Z",
        ],
    )
    _prepare_two_index_odds(f01_out, 1.80)
    _run(
        REPO / "F02_MNEMOS" / "CODEBASE",
        [
            "--in",
            str(f01_out),
            "--out",
            str(f02_out),
            "--snapshots",
            str(snaps),
            "--exports",
            str(exports),
            "--captured-at",
            "2026-11-07T12:00:00Z",
        ],
    )
    snaps_json = [d for d in _jsons(f02_out) if d.get("match_key") and isinstance(d.get("points"), list)]
    assert snaps_json

    _run(
        REPO / "F03_SPECULUM" / "CODEBASE",
        ["--in", str(f02_out), "--out", str(f03_out), "--seen", str(tmp_path / "alert_seen.json")],
    )
    evos = [d for d in _jsons(f03_out) if d.get("contract") == "vanus.evolution.v1"]
    alerts = [d for d in _jsons(f03_out) if d.get("contract") == "vanus.alert.v1"]
    assert evos
    for evo in evos:
        validate_instance(evo, "schema_evolution.json")
    assert alerts
    for alert in alerts:
        validate_instance(alert, "schema_alert.json")

    for src in (f01_out, f03_out):
        for path in src.glob("*.json"):
            (f05_in / path.name).write_bytes(path.read_bytes())
    _run(
        REPO / "F05_CELL" / "CODEBASE",
        ["--in", str(f05_in), "--out", str(f05_out)],
    )
    home = (f05_out / "index.html").read_text(encoding="utf-8")
    assert "CELL" in home
    popup = next(f05_out.glob("match_*.html")).read_text(encoding="utf-8")
    assert "pas trouve" in popup or "Athletic" in popup or "Malaga" in popup or "Evolution" in popup

    sent: list[dict] = []

    def post(url: str, payload: dict) -> dict:
        sent.append({"url": url, "payload": payload})
        return {"ok": True}

    cipher = _load("cipher_e2e", REPO / "F04_CIPHER" / "CODEBASE" / "cipher.py")
    receipts = cipher.deliver(alerts, "tok-test", "chat-1", set(), post=post)
    assert receipts
    assert sent
    assert "sendMessage" in sent[0]["url"]
    env = {k: v for k, v in __import__("os").environ.items() if k not in ("VANUS_TELEGRAM_TOKEN", "VANUS_TELEGRAM_CHAT_ID")}
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "F04_CIPHER" / "CODEBASE" / "run.py"),
            "--in",
            str(f03_out),
            "--out",
            str(f04_out),
            "--seen",
            str(tmp_path / "cipher_seen.json"),
        ],
        cwd=str(REPO / "F04_CIPHER" / "CODEBASE"),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    assert proc.returncode == 0
    assert "token absent" in proc.stderr


def test_ci_workflow_pytest_only_no_cron():
    workflow = REPO / ".github" / "workflows" / "pytest.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "schedule:" not in text
    assert "cron:" not in text
    assert "workflow_dispatch" not in text or "pytest" in text
