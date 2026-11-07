from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from tests.helpers import validate_instance

REPO = Path(__file__).resolve().parents[1]
CODEBASE = REPO / "F02_MNEMOS" / "CODEBASE"


def _load_blogs():
    path = CODEBASE / "blogs.py"
    spec = importlib.util.spec_from_file_location("blogs", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _article(body: str, title: str = "Example") -> dict:
    return {
        "index": "footinsights",
        "url": "https://footinsights.com/blog/example",
        "title": title,
        "body": body,
    }


def test_first_run_is_new(tmp_path):
    blogs = _load_blogs()
    rec = blogs.archive_blog(_article("# Example\n\nhello\n"), "2026-11-07T10:00:00Z", tmp_path / "blogs")
    validate_instance(rec, "schema_blog.json")
    assert rec["status"] == "new"
    assert rec["path"] == "ARCHIVUM/blogs/footinsights/example.md"
    assert rec["content_hash"].startswith("sha256:")
    dest = tmp_path / "blogs" / "footinsights" / "example.md"
    assert dest.read_text(encoding="utf-8") == "# Example\n\nhello\n"
    assert rec["content_hash"] == blogs.hash_content("# Example\n\nhello\n")


def test_second_identical_is_unchanged(tmp_path):
    blogs = _load_blogs()
    store = tmp_path / "blogs"
    first = blogs.archive_blog(_article("same\n"), "2026-11-07T10:00:00Z", store)
    second = blogs.archive_blog(_article("same\n"), "2026-11-07T12:00:00Z", store)
    validate_instance(second, "schema_blog.json")
    assert first["status"] == "new"
    assert second["status"] == "unchanged"
    assert second["content_hash"] == first["content_hash"]
    dest = store / "footinsights" / "example.md"
    assert dest.read_text(encoding="utf-8") == "same\n"


def test_content_change_is_updated(tmp_path):
    blogs = _load_blogs()
    store = tmp_path / "blogs"
    first = blogs.archive_blog(_article("v1\n"), "2026-11-07T10:00:00Z", store)
    second = blogs.archive_blog(_article("v2\n"), "2026-11-07T12:00:00Z", store)
    validate_instance(second, "schema_blog.json")
    assert first["status"] == "new"
    assert second["status"] == "updated"
    assert second["content_hash"] != first["content_hash"]
    dest = store / "footinsights" / "example.md"
    assert dest.read_text(encoding="utf-8") == "v2\n"


def test_empty_articles_no_crash(tmp_path):
    blogs = _load_blogs()
    assert blogs.load_articles(tmp_path / "missing") == []
    empty = tmp_path / "empty.json"
    empty.write_text("{}\n", encoding="utf-8")
    assert blogs.load_articles(empty) == []


def test_golden_fixture_still_valid():
    golden = json.loads((REPO / "tests" / "fixtures" / "json" / "blog.json").read_text(encoding="utf-8"))
    validate_instance(golden, "schema_blog.json")
    assert golden["status"] == "new"


def test_run_blogs_writes_copy_and_meta(tmp_path):
    src = tmp_path / "IN"
    out = tmp_path / "OUT"
    store = tmp_path / "blogs"
    src.mkdir()
    (src / "article.json").write_text(json.dumps(_article("hello\n"), indent=2) + "\n", encoding="utf-8")
    cmd = [
        sys.executable,
        str(CODEBASE / "run.py"),
        "--mode",
        "blogs",
        "--in",
        str(src),
        "--out",
        str(out),
        "--blogs",
        str(store),
        "--captured-at",
        "2026-11-07T10:00:00Z",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=str(CODEBASE))
    paths = [Path(line) for line in proc.stdout.strip().splitlines() if line]
    assert len(paths) == 1
    rec = json.loads(paths[0].read_text(encoding="utf-8"))
    validate_instance(rec, "schema_blog.json")
    assert rec["status"] == "new"
    assert (store / "footinsights" / "example.md").read_text(encoding="utf-8") == "hello\n"
