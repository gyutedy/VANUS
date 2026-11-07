import json
import shutil

import pytest

import VANUS_CUSTOS as custos


def test_load_real_liber(repo_root):
    data = custos.load(repo_root / "liber_vanus.json")
    assert data["contract"] == "vanus.liber.v1"
    assert data["fleet"] == "VANUS"
    assert "status" in data
    assert set(data["frigates"]) >= {
        "F00_INFOCYTE",
        "F01_SCRYER",
        "F02_MNEMOS",
        "F03_SPECULUM",
        "F04_CIPHER",
        "F05_CELL",
        "TARIEL",
    }


def test_round_trip_status(tmp_path, repo_root):
    src = repo_root / "liber_vanus.json"
    copy = tmp_path / "liber_vanus.json"
    shutil.copy(src, copy)
    before = custos.load(copy)
    custos.set_status("phase_01_harness", copy)
    after = custos.load(copy)
    assert after["status"] == "phase_01_harness"
    assert after["frigates"] == before["frigates"]
    assert json.loads(copy.read_text(encoding="utf-8"))["status"] == "phase_01_harness"


def test_set_frigate(tmp_path, repo_root):
    copy = tmp_path / "liber_vanus.json"
    shutil.copy(repo_root / "liber_vanus.json", copy)
    custos.set_frigate("F00_INFOCYTE", "harness", copy)
    assert custos.load(copy)["frigates"]["F00_INFOCYTE"] == "harness"


def test_unknown_frigate_raises(tmp_path, repo_root):
    copy = tmp_path / "liber_vanus.json"
    shutil.copy(repo_root / "liber_vanus.json", copy)
    with pytest.raises(KeyError):
        custos.set_frigate("F99_NOPE", "x", copy)


def test_cli_status(capsys, monkeypatch, repo_root):
    monkeypatch.setattr(custos, "LIBER_PATH", repo_root / "liber_vanus.json")
    assert custos.main(["status"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["contract"] == "vanus.liber.v1"
