from __future__ import annotations

from datetime import datetime


def parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def lecture_open(now: str, kickoffs: list[str], enabled: bool = True) -> bool:
    if not enabled:
        return False
    return not past_all_ko(now, kickoffs)


def alerte_open(now: str, kickoffs: list[str], enabled: bool = True) -> bool:
    if not enabled:
        return False
    return not past_all_ko(now, kickoffs)


def past_all_ko(now: str, kickoffs: list[str]) -> bool:
    if not kickoffs:
        return False
    current = parse_iso(now)
    return all(parse_iso(k) <= current for k in kickoffs)
