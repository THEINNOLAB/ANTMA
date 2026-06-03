"""SQLite FTS adapter."""

from __future__ import annotations

from pathlib import Path

from antma.adapters.base import MemoryBackend
from antma.indexer import MemoryIndex
from antma.schema import MemoryKind, MemoryRecord


class SQLiteFtsBackend(MemoryBackend):
    name = "sqlite_fts"

    def __init__(self, db_path: Path):
        self.index = MemoryIndex(db_path)

    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []
        for result in self.index.search(query, limit=limit):
            records.append(
                MemoryRecord(
                    id=result["path"],
                    kind=MemoryKind(result["kind"]),
                    title=result["title"],
                    body=result["snippet"],
                    source=result["path"],
                )
            )
        return records

