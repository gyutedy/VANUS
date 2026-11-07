from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F05_CELL" / "CODEBASE"
KEY = "laliga:2026-11-07:2000:athletic-club:valencia"


def _load():
    path = CODEBASE / "cell.py"
    spec = importlib.util.spec_from_file_location("cell", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _row(pick: str = "1", home: float = 1.80) -> dict:
    return {
        "home": "Athletic Club",
        "away": "Valencia",
        "kickoff": "2026-11-07T20:00:00Z",
        "score": None,
        "pick": pick,
        "model_pct": 58.0,
        "odds": {"1x2": {"home": home, "draw": 3.4, "away": 4.2}},
        "raw_ref": "archivum/local/predictlix.md",
    }


def _match() -> dict:
    return {
        "contract": "vanus.match.v1",
        "match_key": KEY,
        "competition": "LaLiga",
        "slate_date": "2026-11-07",
        "home": "Athletic Club",
        "away": "Valencia",
        "kickoff": "2026-11-07T20:00:00Z",
        "score": None,
        "indexes": {
            "predictlix": _row("1", 1.80),
            "dailysportpick": None,
            "metapred": {
                "pick": "1",
                "odds": {"1x2": {"home": 1.78, "draw": 3.5, "away": 4.1}},
            },
        },
    }


def _evo() -> dict:
    return {
        "contract": "vanus.evolution.v1",
        "match_key": KEY,
        "market": "1x2",
        "selection": "home",
        "lines": [
            {
                "index": "predictlix",
                "role": "index",
                "points": [
                    {"at": "2026-11-07T10:00:00Z", "odds": 1.90},
                    {"at": "2026-11-07T12:00:00Z", "odds": 1.80},
                ],
            },
            {
                "index": "metapred",
                "role": "index",
                "points": [
                    {"at": "2026-11-07T10:00:00Z", "odds": 1.88},
                    {"at": "2026-11-07T12:00:00Z", "odds": 1.78},
                ],
            },
        ],
    }


def _alert() -> dict:
    return {
        "contract": "vanus.alert.v1",
        "match_key": KEY,
        "level": "alarm",
        "market": "1x2",
        "selection": "home",
        "direction": "shortening",
        "agreeing": ["predictlix", "metapred"],
        "found": ["predictlix", "metapred"],
        "pinnacle_agrees": None,
        "fingerprint": f"{KEY}:1x2:home:shortening:predictlix+metapred",
        "at": "2026-11-07T12:00:00Z",
    }


def _write_out(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "match_one.json").write_text(json.dumps(_match(), indent=2) + "\n", encoding="utf-8")
    (root / "evolution_one.json").write_text(json.dumps(_evo(), indent=2) + "\n", encoding="utf-8")
    (root / "alert_one.json").write_text(json.dumps(_alert(), indent=2) + "\n", encoding="utf-8")


def _get(url: str) -> tuple[int, str]:
    with urlopen(url, timeout=3) as resp:
        return resp.status, resp.read().decode("utf-8")


def test_http_fixture_out_to_html(tmp_path):
    cell = _load()
    src = tmp_path / "OUT"
    _write_out(src)
    store = cell.load_store(src)
    httpd = cell.bind_server(store, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        status, body = _get(f"http://127.0.0.1:{port}/")
        assert status == 200
        assert "PredictLix" in body
        assert "MetaPred" in body
        assert "CELL" in body
        st2, idx = _get(f"http://127.0.0.1:{port}/i/predictlix")
        assert st2 == 200
        assert "LaLiga" in idx
        st3, slate = _get(f"http://127.0.0.1:{port}/i/predictlix/c/laliga")
        assert st3 == 200
        assert "Athletic Club" in slate
        assert "Valencia" in slate
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_popup_match_key(tmp_path):
    cell = _load()
    src = tmp_path / "OUT"
    _write_out(src)
    store = cell.load_store(src)
    httpd = cell.bind_server(store, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        status, body = _get(f"http://127.0.0.1:{port}/m/{quote(KEY, safe='')}")
        assert status == 200
        assert "Athletic Club" in body
        assert "Valencia" in body
        assert "LaLiga" in body
        assert "1X2" in body
        assert "pas trouve" in body
        assert "DailySportPick" in body
        assert "Evolution" in body
        assert "2026-11-07T10:00:00Z" in body
        assert "alarm" in body
        assert "pick : 1" in body
        assert "raw_ref : archivum/local/predictlix.md" in body
        assert 'href="http' not in body.split("raw_ref")[-1][:80]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_empty_drawer_pas_trouve(tmp_path):
    cell = _load()
    src = tmp_path / "OUT"
    _write_out(src)
    html = cell.render_popup(cell.load_store(src), KEY)
    assert "pas trouve" in html
    assert "DailySportPick" in html
    assert "PredictLix" in html


def test_unknown_match_pas_trouve(tmp_path):
    cell = _load()
    store = cell.load_store(tmp_path)
    status, body = cell.route(store, "/m/nope:missing")
    assert status == 404
    assert "pas trouve" in body


def test_cell_does_not_fetch_outbound(tmp_path, monkeypatch):
    cell = _load()
    src = tmp_path / "OUT"
    _write_out(src)

    def boom(*_a, **_k):
        raise AssertionError("outbound HTTP")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    store = cell.load_store(src)
    home = cell.render_home(store)
    popup = cell.render_popup(store, KEY)
    assert "PredictLix" in home
    assert "Athletic Club" in popup
    source = (CODEBASE / "cell.py").read_text(encoding="utf-8")
    assert "urllib.request" not in source
    assert "requests" not in source
    assert "F00_" not in source
    assert "F01_" not in source
    assert "F02_" not in source
    assert "F03_" not in source
    assert "F04_" not in source


def test_run_dump_writes_html(tmp_path):
    src = tmp_path / "IN"
    out = tmp_path / "OUT"
    _write_out(src)
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--in",
        str(src),
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    names = {Path(line).name for line in proc.stdout.strip().splitlines() if line}
    assert "index.html" in names
    assert any(n.startswith("match_") for n in names)
    home = (out / "index.html").read_text(encoding="utf-8")
    assert "PredictLix" in home
    popup = next(out.glob("match_*.html")).read_text(encoding="utf-8")
    assert "Athletic Club" in popup
    assert "pas trouve" in popup
    assert "Evolution" in popup


def test_skin_plaque_and_dalles(tmp_path):
    cell = _load()
    src = tmp_path / "OUT"
    _write_out(src)
    store = cell.load_store(src)
    home = cell.render_home(store)
    assert "Officio Assassinorum" in home
    assert "TEMPLE VANUS" in home
    assert 'class="dalle"' in home
    assert "polyline" not in home
    popup = cell.render_popup(store, KEY)
    assert "Officio Assassinorum" in popup
    assert "TEMPLE VANUS" in popup
    assert "<polyline" in popup
    assert 'aria-label="evolution"' in popup
    assert "attente 2e releve" not in popup


def test_one_poll_point_waits_second_reading(tmp_path):
    cell = _load()
    src = tmp_path / "OUT"
    _write_out(src)
    evo = _evo()
    evo["lines"] = [
        {
            "index": "predictlix",
            "role": "index",
            "points": [{"at": "2026-11-07T10:00:00Z", "odds": 1.90}],
        }
    ]
    (src / "evolution_one.json").write_text(json.dumps(evo, indent=2) + "\n", encoding="utf-8")
    html = cell.render_popup(cell.load_store(src), KEY)
    assert "attente 2e releve" in html
    assert "<circle" in html
    assert "<polyline" not in html
