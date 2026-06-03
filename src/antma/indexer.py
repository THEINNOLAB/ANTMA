"""SQLite FTS index for Markdown workspaces."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from antma.resolver import resolve
from antma.schema import MemoryKind, MemoryRecord, utc_now


INDEX_SCHEMA_VERSION = 1
WORKSPACE_SCHEMA_VERSION = 1
META_TABLE = "antma_meta"


IGNORED_INDEX_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".antma",
    ".openclaw",
    "dist",
    "build",
}


class IndexCompatibilityError(RuntimeError):
    """Raised when an index is missing or must be rebuilt."""


def infer_kind(path: Path) -> str:
    parts = set(path.parts)
    if "ssot" in parts:
        return "source_of_truth"
    if "agents" in parts:
        return "agent_local"
    if "daily" in parts:
        return "daily_raw"
    if "knowledge-bank" in parts:
        return "knowledge_bank"
    if "promotions" in parts:
        return "promotion_candidate"
    if "evidence" in parts:
        return "evidence_packet"
    if path.name == "MEMORY.shared.md":
        return "shared_memory"
    return "knowledge_bank"


class MemoryIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        return self.connect_write()

    def connect_write(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def connect_read(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise IndexCompatibilityError(rebuild_index_message(self.db_path, "Index DB is missing."))
        uri = "file:" + quote(str(self.db_path.resolve()), safe="/:") + "?mode=ro"
        try:
            return sqlite3.connect(uri, uri=True)
        except sqlite3.Error as error:
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, f"Index DB cannot be opened read-only: {error}.")
            ) from error

    def initialize(self) -> None:
        with self.connect_write() as conn:
            self._initialize_schema(conn)
            self._write_metadata(conn)

    def clear(self) -> None:
        with self.connect_write() as conn:
            self._rebuild_schema(conn)
            self._write_metadata(conn)

    def index_markdown_tree(self, root: Path) -> int:
        root = root.resolve()
        count = 0
        with self.connect_write() as conn:
            self._rebuild_schema(conn)
            for path in sorted(root.rglob("*.md")):
                relative = path.relative_to(root)
                if should_skip_index_path(relative):
                    continue
                body = path.read_text(encoding="utf-8")
                title = first_heading(body) or path.stem
                kind = infer_kind(relative)
                conn.execute(
                    "INSERT INTO memories(path, title, kind, body) VALUES (?, ?, ?, ?)",
                    (str(relative), title, kind, body),
                )
                count += 1
            self._write_metadata(conn)
        return count

    def search(self, query: str, limit: int = 10) -> list[dict[str, str]]:
        try:
            with self.connect_read() as conn:
                self.validate_connection(conn)
                return self._search_validated(conn, query=query, limit=limit)
        except sqlite3.Error as error:
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, f"Index DB cannot be searched: {error}.")
            ) from error

    def validate(self) -> dict[str, str]:
        try:
            with self.connect_read() as conn:
                return self.validate_connection(conn)
        except sqlite3.Error as error:
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, f"Index DB cannot be inspected: {error}.")
            ) from error

    def validate_connection(self, conn: sqlite3.Connection) -> dict[str, str]:
        if not table_exists(conn, META_TABLE):
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, "Index DB is missing ANTMA metadata.")
            )
        metadata = read_metadata(conn)
        index_version = metadata.get("index_schema_version")
        if index_version is None:
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, "Index DB metadata has no index_schema_version.")
            )
        if index_version != str(INDEX_SCHEMA_VERSION):
            raise IndexCompatibilityError(
                rebuild_index_message(
                    self.db_path,
                    f"Index DB schema version {index_version!r} is not supported.",
                )
            )
        workspace_version = metadata.get("workspace_schema_version")
        if workspace_version is None:
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, "Index DB metadata has no workspace_schema_version.")
            )
        if workspace_version != str(WORKSPACE_SCHEMA_VERSION):
            raise IndexCompatibilityError(
                rebuild_index_message(
                    self.db_path,
                    f"Workspace schema version {workspace_version!r} in index metadata is not supported.",
                )
            )
        if not metadata.get("indexed_at"):
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, "Index DB metadata has no indexed_at timestamp.")
            )
        if not table_exists(conn, "memories"):
            raise IndexCompatibilityError(
                rebuild_index_message(self.db_path, "Index DB has no searchable memories table.")
            )
        return metadata

    def _search_validated(self, conn: sqlite3.Connection, query: str, limit: int) -> list[dict[str, str]]:
        query = query.strip()
        if limit <= 0 or not query:
            return []
        rows = self._search_rows(conn, query)
        records: list[MemoryRecord] = []
        snippets: dict[str, str] = {}
        for path, title, kind, body, snippet in rows:
            record = MemoryRecord(
                id=path,
                kind=MemoryKind(kind),
                title=title,
                body=body,
                source=path,
            )
            records.append(record)
            snippets[path] = snippet
        return [
            {
                "path": record.id,
                "title": record.title,
                "kind": record.kind.value,
                "snippet": snippets.get(record.id, ""),
            }
            for record in resolve(records, query=query, limit=limit)
        ]

    def _search_rows(
        self,
        conn: sqlite3.Connection,
        query: str,
    ) -> list[tuple[str, str, str, str, str]]:
        sql = """
            SELECT path, title, kind, body, snippet(memories, 3, '[', ']', ' ... ', 12)
            FROM memories
            WHERE memories MATCH ?
            """
        try:
            return conn.execute(sql, (query,)).fetchall()
        except sqlite3.OperationalError:
            fallback_query = as_plain_text_fts_query(query)
            if not fallback_query or fallback_query == query:
                raise
            return conn.execute(sql, (fallback_query,)).fetchall()

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memories
            USING fts5(path, title, kind, body)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS antma_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

    def _rebuild_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute("DROP TABLE IF EXISTS memories")
        conn.execute("DROP TABLE IF EXISTS antma_meta")
        self._initialize_schema(conn)

    def _write_metadata(self, conn: sqlite3.Connection) -> None:
        metadata = {
            "index_schema_version": str(INDEX_SCHEMA_VERSION),
            "workspace_schema_version": str(WORKSPACE_SCHEMA_VERSION),
            "indexed_at": utc_now(),
        }
        conn.executemany(
            "INSERT OR REPLACE INTO antma_meta(key, value) VALUES (?, ?)",
            sorted(metadata.items()),
        )


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def read_metadata(conn: sqlite3.Connection) -> dict[str, str]:
    return dict(conn.execute("SELECT key, value FROM antma_meta").fetchall())


def rebuild_index_message(db_path: Path, problem: str) -> str:
    return f"{problem} Run: antma index PATH --db {db_path}"


def should_skip_index_path(relative: Path) -> bool:
    return any(part in IGNORED_INDEX_PARTS or part.endswith(".egg-info") for part in relative.parts)


def first_heading(markdown: str) -> Optional[str]:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def as_plain_text_fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    return " ".join(f'"{token}"' for token in tokens)
