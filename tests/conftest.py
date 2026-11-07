from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / "CONTRACTS"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="run live HTTP tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="live HTTP skipped (pass --live)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def repo_root():
    return REPO_ROOT


@pytest.fixture
def contracts_dir():
    return CONTRACTS_DIR


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR
