from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F04_CIPHER" / "CODEBASE"
KEY = "laliga:2026-11-07:2000:athletic-club:valencia"


def _load():
    path = CODEBASE / "cipher.py"
    spec = importlib.util.spec_from_file_location("cipher", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _alert(level: str = "alarm", agreeing: list[str] | None = None) -> dict:
    names = agreeing or ["predictlix", "metapred"]
    payload = {
        "contract": "vanus.alert.v1",
        "match_key": KEY,
        "level": level,
        "market": "1x2",
        "selection": "home",
        "direction": "shortening",
        "agreeing": names,
        "found": ["predictlix", "metapred", "dailysportpick"] if level == "alarm" else names,
        "pinnacle_agrees": None,
        "fingerprint": f"{KEY}:1x2:home:shortening:{'+'.join(names)}",
        "at": "2026-11-07T12:00:00Z",
    }
    validate_instance(payload, "schema_alert.json")
    return payload


def test_mocked_telegram_sends_once():
    cp = _load()
    sent: list[dict] = []

    def post(url: str, payload: dict) -> dict:
        sent.append({"url": url, "payload": payload})
        return {"ok": True}

    seen: set[str] = set()
    alert = _alert("alarm")
    first = cp.deliver([alert], "tok-test", "chat-1", seen, post=post)
    second = cp.deliver([alert], "tok-test", "chat-1", seen, post=post)
    assert len(sent) == 1
    assert len(first) == 1
    assert second == []
    assert "sendMessage" in sent[0]["url"]
    assert sent[0]["payload"]["chat_id"] == "chat-1"
    assert "ALARME" in sent[0]["payload"]["text"]
    assert alert["fingerprint"] in seen


def test_same_alert_one_send():
    cp = _load()
    sent: list[dict] = []

    def post(url: str, payload: dict) -> dict:
        sent.append(payload)
        return {"ok": True}

    seen: set[str] = set()
    batch = [_alert("alarm"), _alert("alarm")]
    cp.deliver(batch, "tok-test", "chat-1", seen, post=post)
    assert len(sent) == 1


def test_jackpot_differs_from_alarm():
    cp = _load()
    alarm = cp.format_message(_alert("alarm"))
    jackpot = cp.format_message(_alert("jackpot", ["predictlix", "metapred", "dailysportpick"]))
    assert alarm != jackpot
    assert alarm.startswith("ALARME")
    assert jackpot.startswith("JACKPOT")
    sent: list[str] = []

    def post(url: str, payload: dict) -> dict:
        sent.append(payload["text"])
        return {"ok": True}

    cp.deliver(
        [
            _alert("alarm"),
            _alert("jackpot", ["predictlix", "metapred", "dailysportpick"]),
        ],
        "tok-test",
        "chat-1",
        set(),
        post=post,
    )
    assert len(sent) == 2
    assert sent[0] != sent[1]
    assert sent[0].startswith("ALARME")
    assert sent[1].startswith("JACKPOT")


def test_token_absent_logs_no_crash():
    cp = _load()
    sent: list[dict] = []

    def post(url: str, payload: dict) -> dict:
        sent.append(payload)
        return {"ok": True}

    class Buf:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def write(self, msg: str) -> None:
            self.lines.append(msg)

    log = Buf()
    out = cp.deliver([_alert()], "", "chat-1", set(), post=post, log=log)
    assert out == []
    assert sent == []
    assert any("token absent" in line for line in log.lines)
    out2 = cp.deliver([_alert()], "tok-test", "", set(), post=post, log=log)
    assert out2 == []
    assert sent == []


def test_credentials_from_env_not_files(tmp_path):
    cp = _load()
    (tmp_path / "token").write_text("should-not-read\n", encoding="utf-8")
    env = {cp.ENV_TOKEN: "from-env", cp.ENV_CHAT: "42"}
    token, chat = cp.credentials(env)
    assert token == "from-env"
    assert chat == "42"
    empty_token, empty_chat = cp.credentials({})
    assert empty_token == ""
    assert empty_chat == ""
    source = (CODEBASE / "cipher.py").read_text(encoding="utf-8")
    assert "F00_" not in source
    assert "F01_" not in source
    assert "F02_" not in source
    assert "F03_" not in source
    assert "F05_" not in source


def test_run_token_absent_exit_zero(tmp_path):
    src = tmp_path / "IN"
    out = tmp_path / "OUT"
    src.mkdir()
    out.mkdir()
    (src / "alert_one.json").write_text(json.dumps(_alert(), indent=2) + "\n", encoding="utf-8")
    env = {k: v for k, v in __import__("os").environ.items() if k not in ("VANUS_TELEGRAM_TOKEN", "VANUS_TELEGRAM_CHAT_ID")}
    proc = subprocess.run(
        [
            sys.executable,
            str(CODEBASE / "run.py"),
            "--in",
            str(src),
            "--out",
            str(out),
            "--seen",
            str(tmp_path / "seen.json"),
        ],
        capture_output=True,
        text=True,
        cwd=str(CODEBASE),
        env=env,
        check=False,
    )
    assert proc.returncode == 0
    assert "token absent" in proc.stderr
    assert not (out / "cipher_sent.json").exists()
