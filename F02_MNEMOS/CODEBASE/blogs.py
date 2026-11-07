from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CONTRACT = "vanus.blog.v1"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def hash_content(body: str) -> str:
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def blog_slug(url: str) -> str:
    parsed = urlparse(url)
    tail = parsed.path.rstrip("/").split("/")[-1] if parsed.path else ""
    slug = _NON_ALNUM.sub("-", tail.lower()).strip("-")
    return slug or "unknown"


def blog_relpath(index: str, url: str) -> str:
    return f"ARCHIVUM/blogs/{index}/{blog_slug(url)}.md"


def load_articles(src: Path) -> list[dict[str, Any]]:
    if src.is_file():
        return _as_articles(json.loads(src.read_text(encoding="utf-8")))
    articles: list[dict[str, Any]] = []
    if not src.is_dir():
        return articles
    for path in sorted(src.glob("*.json")):
        articles.extend(_as_articles(json.loads(path.read_text(encoding="utf-8"))))
    return articles


def archive_blog(
    article: dict[str, Any],
    captured_at: str,
    blogs_dir: Path,
) -> dict[str, Any]:
    index = str(article.get("index") or "footinsights")
    url = str(article.get("url") or "")
    title = str(article.get("title") or "")
    body = str(article.get("body") or "")
    rel = blog_relpath(index, url)
    dest = blogs_dir / index / f"{blog_slug(url)}.md"
    digest = hash_content(body)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        previous = dest.read_text(encoding="utf-8")
        status = "unchanged" if hash_content(previous) == digest else "updated"
    else:
        status = "new"
    if status != "unchanged":
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(dest)
    record = {
        "contract": CONTRACT,
        "index": index,
        "url": url,
        "title": title,
        "captured_at": captured_at,
        "content_hash": digest,
        "path": rel,
        "status": status,
    }
    return record


def write_blog(record: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = blog_slug(str(record.get("url") or ""))
    index = str(record.get("index") or "unknown")
    target = out_dir / f"blog_{index}_{slug}.json"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def _as_articles(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if _is_article(item)]
    if isinstance(data, dict) and _is_article(data):
        return [data]
    if isinstance(data, dict) and isinstance(data.get("articles"), list):
        return [item for item in data["articles"] if _is_article(item)]
    return []


def _is_article(item: Any) -> bool:
    return isinstance(item, dict) and bool(item.get("url")) and "body" in item
