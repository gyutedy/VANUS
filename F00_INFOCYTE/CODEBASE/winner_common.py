#!/usr/bin/env python3
"""
WINNER COMMON — socle du capteur winner.bet (lecture seule, stdlib).
===================================================================
- lecture publique SANS login, cookie de session ni pari ;
- cadence basse (T-2h / T-0) ;
- HTML BRUT archive AVANT tout parsing (tracabilite) ;
- cellule absente = None + trou nomme, jamais 0, jamais estimee ;
- aucune probabilite produite ici : ce sont des OBSERVATIONS.
"""
from __future__ import annotations

import hashlib
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TIMEOUT_S = 30
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _norm(value: Any) -> str:
    return _WS.sub(" ", _TAG.sub(" ", str(value or ""))).strip()


def _alnum(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def match_key(home: Any, away: Any, date: str | None = None) -> str | None:
    """Convention F01 SCRYER : alnum minuscule, tries, date optionnelle."""
    h, a = _alnum(home), _alnum(away)
    if not h or not a:
        return None
    base = "_".join(sorted([h, a]))
    return f"{base}_{date}" if date else base


def fetch(url: str, archive_dir: str | Path) -> tuple[str, list[str]]:
    """Telecharge la page publique une fois, archive le HTML brut.
    Echec reseau = (vide, [trou]), jamais d'exception remontee."""
    holes: list[str] = []
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return "", ["fetch_failed:" + type(exc).__name__]
    if not html.strip():
        return "", ["reponse_vide"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha1(url.encode()).hexdigest()[:10]
    arch = Path(archive_dir)
    arch.mkdir(parents=True, exist_ok=True)
    (arch / f"winner_{stamp}_{digest}.html").write_text(html, encoding="utf-8")
    return html, holes


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(raw: Any) -> float | None:
    """Cote ou None. '1.85 ', '-', '', '—' -> None. Jamais 0 par defaut."""
    txt = _norm(raw).replace(",", ".")
    if not txt:
        return None
    try:
        val = float(txt)
    except ValueError:
        return None
    return val if val > 1.0 else None


def _line(raw: Any) -> float | None:
    """Ligne de total (ex. 226.5) ou None."""
    txt = _norm(raw).replace(",", ".")
    if not txt:
        return None
    try:
        return float(txt)
    except ValueError:
        return None
