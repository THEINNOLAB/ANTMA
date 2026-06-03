import sqlite3
from pathlib import Path

import pytest

from antma.indexer import IndexCompatibilityError, MemoryIndex, as_plain_text_fts_query


def test_search_applies_antma_priority_after_fts_match(tmp_path: Path):
    root = tmp_path / "team-memory"
    (root / "daily").mkdir(parents=True)
    (root / "ssot").mkdir(parents=True)
    (root / "daily" / "launch.md").write_text(
        "# Launch Raw\n\nlaunch decision was discussed in raw notes.",
        encoding="utf-8",
    )
    (root / "ssot" / "launch.md").write_text(
        "# Launch Truth\n\nlaunch decision is approved as current truth.",
        encoding="utf-8",
    )
    index = MemoryIndex(tmp_path / "index.db")
    index.index_markdown_tree(root)

    results = index.search("launch decision")

    assert results[0]["path"] == "ssot/launch.md"
    assert results[0]["kind"] == "source_of_truth"


def test_search_priority_considers_matches_beyond_initial_fts_order(tmp_path: Path):
    root = tmp_path / "team-memory"
    (root / "daily").mkdir(parents=True)
    (root / "ssot").mkdir(parents=True)
    for number in range(30):
        (root / "daily" / f"launch-{number:02d}.md").write_text(
            f"# Launch Raw {number}\n\nlaunch decision was discussed in raw notes.",
            encoding="utf-8",
        )
    (root / "ssot" / "launch.md").write_text(
        "# Launch Truth\n\nlaunch decision is approved as current truth.",
        encoding="utf-8",
    )
    index = MemoryIndex(tmp_path / "index.db")
    index.index_markdown_tree(root)

    results = index.search("launch decision", limit=1)

    assert results[0]["path"] == "ssot/launch.md"
    assert results[0]["kind"] == "source_of_truth"


def test_search_falls_back_for_hyphenated_plain_text_query(tmp_path: Path):
    root = tmp_path / "team-memory"
    (root / "daily").mkdir(parents=True)
    (root / "ssot").mkdir(parents=True)
    (root / "daily" / "truth.md").write_text(
        "# Raw Truth Note\n\nsource-of-truth was mentioned but not reviewed.",
        encoding="utf-8",
    )
    (root / "ssot" / "truth.md").write_text(
        "# Source Truth\n\nsource-of-truth policy is the reviewed rule.",
        encoding="utf-8",
    )
    index = MemoryIndex(tmp_path / "index.db")
    index.index_markdown_tree(root)

    results = index.search("source-of-truth")

    assert results[0]["path"] == "ssot/truth.md"
    assert results[0]["kind"] == "source_of_truth"


def test_plain_text_fts_query_quotes_user_tokens():
    assert as_plain_text_fts_query('source-of-truth OR "memory"') == (
        '"source" "of" "truth" "OR" "memory"'
    )


def test_index_writes_compatibility_metadata_without_local_paths(tmp_path: Path):
    root = tmp_path / "team-memory"
    (root / "ssot").mkdir(parents=True)
    (root / "ssot" / "truth.md").write_text("# Truth\n\nReviewed.", encoding="utf-8")
    db_path = root / ".antma" / "index.db"

    MemoryIndex(db_path).index_markdown_tree(root)

    with sqlite3.connect(db_path) as conn:
        metadata = dict(conn.execute("SELECT key, value FROM antma_meta").fetchall())

    assert metadata["index_schema_version"] == "1"
    assert metadata["workspace_schema_version"] == "1"
    assert metadata["indexed_at"]
    assert str(root) not in "\n".join(metadata.values())


def test_search_missing_db_raises_without_creating_db(tmp_path: Path):
    db_path = tmp_path / "missing" / "index.db"

    with pytest.raises(IndexCompatibilityError, match="Index DB is missing"):
        MemoryIndex(db_path).search("launch")

    assert not db_path.exists()


def test_search_legacy_db_without_metadata_requires_reindex(tmp_path: Path):
    db_path = tmp_path / "index.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE VIRTUAL TABLE memories
            USING fts5(path, title, kind, body)
            """
        )

    with pytest.raises(IndexCompatibilityError, match="missing ANTMA metadata"):
        MemoryIndex(db_path).search("launch")


def test_index_rebuilds_unsupported_derived_index(tmp_path: Path):
    root = tmp_path / "team-memory"
    (root / "ssot").mkdir(parents=True)
    (root / "ssot" / "truth.md").write_text("# Truth\n\nlaunch approved.", encoding="utf-8")
    db_path = root / ".antma" / "index.db"
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE VIRTUAL TABLE memories
            USING fts5(path, title, kind, body)
            """
        )
        conn.execute("CREATE TABLE antma_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO antma_meta(key, value) VALUES (?, ?)", ("index_schema_version", "999"))
        conn.execute("INSERT INTO antma_meta(key, value) VALUES (?, ?)", ("workspace_schema_version", "1"))
        conn.execute("INSERT INTO antma_meta(key, value) VALUES (?, ?)", ("indexed_at", "2026-06-02T00:00:00+00:00"))

    count = MemoryIndex(db_path).index_markdown_tree(root)
    results = MemoryIndex(db_path).search("launch")

    assert count == 1
    assert results[0]["path"] == "ssot/truth.md"
