from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ALERT_CONTRACT = "vanus.alert.v1"
ENV_TOKEN = "VANUS_TELEGRAM_TOKEN"
ENV_CHAT = "VANUS_TELEGRAM_CHAT_ID"
API_TMPL = "https://api.telegram.org/bot{token}/sendMessage"

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
PostFn = Callable[[str, dict[str, Any]], dict[str, Any]]


def load_alerts(src: Path) -> list[dict[str, Any]]:
    if src.is_file():
        data = json.loads(src.read_text(encoding="utf-8"))
        return [data] if _is_alert(data) else []
    out: list[dict[str, Any]] = []
    if not src.is_dir():
        return out
    for path in sorted(src.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _is_alert(data):
            out.append(data)
    return out


def load_seen(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {str(x) for x in raw}
    if isinstance(raw, dict) and isinstance(raw.get("fingerprints"), list):
        return {str(x) for x in raw["fingerprints"]}
    return set()


def save_seen(seen: set[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprints": sorted(seen)}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def credentials(env: dict[str, str] | None = None) -> tuple[str, str]:
    source = env if env is not None else os.environ
    token = str(source.get(ENV_TOKEN) or "").strip()
    chat = str(source.get(ENV_CHAT) or "").strip()
    return token, chat


def format_message(alert: dict[str, Any]) -> str:
    level = str(alert.get("level") or "")
    head = "JACKPOT" if level == "jackpot" else "ALARME"
    key = str(alert.get("match_key") or "")
    market = str(alert.get("market") or "")
    selection = str(alert.get("selection") or "")
    direction = str(alert.get("direction") or "")
    agreeing = " + ".join(str(x) for x in (alert.get("agreeing") or []))
    found = " + ".join(str(x) for x in (alert.get("found") or []))
    lines = [
        f"{head} {key}".strip(),
        " ".join(p for p in (market, selection, direction) if p),
        f"agreeing: {agreeing}" if agreeing else "",
        f"found: {found}" if found else "",
    ]
    pin = alert.get("pinnacle_agrees")
    if pin is True:
        lines.append("pinnacle: juge")
    elif pin is False:
        lines.append("pinnacle: desaccord")
    return "\n".join(p for p in lines if p)


def deliver(
    alerts: list[dict[str, Any]],
    token: str,
    chat_id: str,
    seen: set[str] | None = None,
    post: PostFn | None = None,
    log: Any = None,
) -> list[dict[str, Any]]:
    known = seen if seen is not None else set()
    sender = post or post_json
    receipts: list[dict[str, Any]] = []
    if not token or not chat_id:
        _log(log, "token absent")
        return receipts
    url = API_TMPL.format(token=token)
    for alert in alerts:
        fp = str(alert.get("fingerprint") or "")
        if not fp or fp in known:
            continue
        text = format_message(alert)
        sender(url, {"chat_id": chat_id, "text": text})
        known.add(fp)
        receipts.append(
            {
                "fingerprint": fp,
                "level": alert.get("level"),
                "match_key": alert.get("match_key"),
                "text": text,
            }
        )
    return receipts


def post_json(url: str, payload: dict[str, Any], timeout: float = 10) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError("telegram unreachable") from exc
    if not raw:
        return {"ok": True}
    data = json.loads(raw)
    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError("telegram rejected")
    return data if isinstance(data, dict) else {"ok": True}


def write_json(data: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def file_slug(match_key: str) -> str:
    return _NON_ALNUM.sub("_", match_key.lower()).strip("_") or "unknown"


def _is_alert(data: Any) -> bool:
    return isinstance(data, dict) and data.get("contract") == ALERT_CONTRACT


def _log(log: Any, msg: str) -> None:
    if log is None:
        return
    log.write(msg + "\n")
