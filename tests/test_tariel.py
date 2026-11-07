from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARIEL_CODE = REPO / "TARIEL" / "CODEBASE"
PA_DIR = REPO / "PA"
KEY = "laliga:2026-11-07:2000:athletic-club:valencia"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _load_tariel():
    sys.path.insert(0, str(TARIEL_CODE))
    return _load("tariel", TARIEL_CODE / "tariel.py")


def _load_gates():
    sys.path.insert(0, str(TARIEL_CODE))
    return _load("gates", TARIEL_CODE / "gates.py")


def _layout(root: Path) -> Path:
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
    return root


def _stub(root: Path) -> Path:
    path = root / "stub_write.py"
    path.write_text(
        "import pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_text('ok\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    return path


def _commands(root: Path, stub: Path) -> dict[str, list[str]]:
    py = sys.executable
    mapping = {
        "F00_INFOCYTE": root / "F00_INFOCYTE" / "OUT" / "slate.json",
        "F01_SCRYER": root / "F01_SCRYER" / "OUT" / "match.json",
        "F02_MNEMOS": root / "F02_MNEMOS" / "OUT" / "snap.json",
        "F03_SPECULUM": root / "F03_SPECULUM" / "OUT" / "evolution.json",
        "F05_CELL": root / "F05_CELL" / "OUT" / "index.html",
        "F04_CIPHER": root / "F04_CIPHER" / "OUT" / "cipher_sent.json",
    }
    return {name: [py, str(stub), str(dest)] for name, dest in mapping.items()}


def _match(kickoff: str = "2026-11-07T20:00:00Z") -> dict:
    return {
        "contract": "vanus.match.v1",
        "match_key": KEY,
        "competition": "LaLiga",
        "slate_date": "2026-11-07",
        "home": "Athletic Club",
        "away": "Valencia",
        "kickoff": kickoff,
        "score": None,
        "indexes": {"predictlix": {"pick": "1"}, "dailysportpick": None},
    }


def test_two_ticks_write_out_files(tmp_path):
    tr = _load_tariel()
    root = _layout(tmp_path)
    stub = _stub(tmp_path)
    cmds = _commands(root, stub)
    times = iter(["2026-11-07T10:00:00Z", "2026-11-07T12:00:00Z"])
    sleeps: list[float] = []
    done = tr.run_loop(
        root,
        now_fn=lambda: next(times),
        sleep_fn=sleeps.append,
        poll_minutes=120,
        ticks=2,
        commands=cmds,
    )
    assert len(done) == 2
    assert sleeps == [120 * 60]
    assert (root / "F00_INFOCYTE" / "OUT" / "slate.json").is_file()
    assert (root / "F01_SCRYER" / "OUT" / "match.json").is_file()
    assert (root / "F02_MNEMOS" / "OUT" / "snap.json").is_file()
    assert (root / "F03_SPECULUM" / "OUT" / "evolution.json").is_file()
    assert (root / "F05_CELL" / "OUT" / "index.html").is_file()
    assert (root / "F04_CIPHER" / "OUT" / "cipher_sent.json").is_file()
    order = [row["step"] for row in done[0]["ran"]]
    assert order == [
        "F00_INFOCYTE",
        "F01_SCRYER",
        "F02_MNEMOS",
        "F03_SPECULUM",
        "F05_CELL",
        "F04_CIPHER",
    ]
    assert [row["gate"] for row in done[0]["ran"][:5]] == ["lecture"] * 5
    assert done[0]["ran"][-1]["gate"] == "alerte"


def test_tariel_does_not_parse_html():
    texts = []
    for name in ("tariel.py", "gates.py", "run.py"):
        texts.append((TARIEL_CODE / name).read_text(encoding="utf-8"))
    texts.append((PA_DIR / "pa_task.py").read_text(encoding="utf-8"))
    texts.append((PA_DIR / "pa_web.py").read_text(encoding="utf-8"))
    blob = "\n".join(texts)
    assert "html.parser" not in blob
    assert "BeautifulSoup" not in blob
    assert "parse_html" not in blob
    assert "from F00" not in blob
    assert "from F01" not in blob
    assert "from F02" not in blob
    assert "from F03" not in blob
    assert "from F04" not in blob
    assert "predictlix" not in blob


def test_poll_floor_thirty():
    tr = _load_tariel()
    assert tr.clamp_poll(15) == 30
    assert tr.clamp_poll(120) == 120
    assert tr.clamp_poll(None) == 120


def test_until_ko_stops_without_tick(tmp_path):
    tr = _load_tariel()
    root = _layout(tmp_path)
    (root / "F01_SCRYER" / "OUT" / "match.json").write_text(
        json.dumps(_match("2026-11-07T11:00:00Z"), indent=2) + "\n",
        encoding="utf-8",
    )
    stub = _stub(tmp_path)
    done = tr.run_loop(
        root,
        now_fn=lambda: "2026-11-07T12:00:00Z",
        sleep_fn=lambda _s: None,
        ticks=5,
        commands=_commands(root, stub),
    )
    assert done == []
    assert not (root / "F00_INFOCYTE" / "OUT" / "slate.json").exists()


def test_gates_lecture_alerte():
    gt = _load_gates()
    now = "2026-11-07T10:00:00Z"
    later = "2026-11-07T21:00:00Z"
    kos = ["2026-11-07T20:00:00Z"]
    assert gt.lecture_open(now, kos) is True
    assert gt.alerte_open(now, kos) is True
    assert gt.lecture_open(later, kos) is False
    assert gt.alerte_open(later, kos) is False
    assert gt.lecture_open(now, [], enabled=False) is False


def test_pa_task_one_pass(tmp_path):
    root = _layout(tmp_path)
    code = root / "TARIEL" / "CODEBASE"
    code.mkdir(parents=True)
    marker = root / "PASS"
    (code / "tariel.py").write_text(
        "from pathlib import Path\n"
        "def now_iso():\n"
        "    return '2026-11-07T10:00:00Z'\n"
        "def one_pass(root, now=None, **kw):\n"
        "    Path(root, 'PASS').write_text((now or 'x') + '\\n', encoding='utf-8')\n"
        "    return {'at': now, 'ran': []}\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(PA_DIR / "pa_task.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8").strip() == "2026-11-07T10:00:00Z"
    source = (PA_DIR / "pa_task.py").read_text(encoding="utf-8")
    assert "while True" not in source
    assert "serve_forever" not in source
    assert "one_pass" in source
    assert "run_loop" not in source


def test_pa_web_get_root(tmp_path):
    root = _layout(tmp_path)
    (root / "F05_CELL" / "IN" / "match.json").write_text(
        json.dumps(_match(), indent=2) + "\n",
        encoding="utf-8",
    )
    pa_web = _load("pa_web", PA_DIR / "pa_web.py")
    app = pa_web.make_app(root)
    captured: list = []

    def start_response(status, headers):
        captured.append((status, headers))

    environ = {"PATH_INFO": "/", "QUERY_STRING": "", "REQUEST_METHOD": "GET"}
    body = b"".join(app(environ, start_response)).decode("utf-8")
    assert captured[0][0].startswith("200")
    assert "CELL" in body
    assert "PredictLix" in body
    source = (PA_DIR / "pa_web.py").read_text(encoding="utf-8")
    assert "F00_" not in source
    assert "F01_" not in source
    assert "F02_" not in source
    assert "F03_" not in source
    assert "F04_" not in source
    assert "urllib.request" not in source
