"""Markdown adapter."""

from __future__ import annotations

from pathlib import Path

from antma.adapters.base import MemoryBackend
from antma.indexer import infer_kind, should_skip_index_path
from antma.resolver import resolve
from antma.schema import MemoryKind, MemoryRecord


class MarkdownBackend(MemoryBackend):
    name = "markdown"

    def __init__(self, root: Path):
        self.root = root

    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        terms = [term.lower() for term in query.split() if term.strip()]
        records: list[MemoryRecord] = []
        for path in sorted(self.root.rglob("*.md")):
            relative = path.relative_to(self.root)
            if should_skip_index_path(relative):
                continue
            body = path.read_text(encoding="utf-8")
            text = body.lower()
            if terms and not all(term in text for term in terms):
                continue
            kind = MemoryKind(infer_kind(relative))
            records.append(MemoryRecord.from_markdown(relative, body, kind))
        return resolve(records, query=query, limit=limit)
