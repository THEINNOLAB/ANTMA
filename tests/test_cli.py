import json
import sqlite3
from pathlib import Path

from antma.cli import main
from antma.indexer import MemoryIndex


def test_promote_command_creates_candidate_and_refuses_overwrite(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    source = root / "daily" / "example.md"
    output = root / "curation" / "promotions" / "example-promotion.md"

    assert main(["promote", str(source), "--reason", "Reviewed durable fact."]) == 0
    text = output.read_text(encoding="utf-8")

    assert "Promotion Candidate" in text
    assert "Reviewed durable fact." in text
    assert "Source hash:" in text
    assert main(["promote", str(source), "--reason", "Again."]) == 1


def test_evidence_command_creates_packet(tmp_path: Path):
    output = tmp_path / "evidence" / "packet.md"

    result = main(
        [
            "evidence",
            "--objective",
            "Ship public hardening",
            "--status",
            "pass",
            "--criterion",
            "tests pass",
            "--evidence",
            "pytest=pass=all tests passed",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    text = output.read_text(encoding="utf-8")
    assert "Ship public hardening" in text
    assert "pytest: pass (all tests passed)" in text


def test_evidence_command_rejects_malformed_evidence(tmp_path: Path):
    output = tmp_path / "packet.md"

    result = main(
        [
            "evidence",
            "--objective",
            "Bad packet",
            "--status",
            "blocked",
            "--criterion",
            "has evidence",
            "--evidence",
            "missing separators",
            "--output",
            str(output),
        ]
    )

    assert result == 2
    assert not output.exists()


def test_search_command_handles_hyphenated_plain_text_query(tmp_path: Path, capsys):
    root = tmp_path / "team-memory"
    (root / "ssot").mkdir(parents=True)
    (root / "ssot" / "truth.md").write_text(
        "# Source Truth\n\nsource-of-truth policy is reviewed.",
        encoding="utf-8",
    )
    db_path = tmp_path / "index.db"
    MemoryIndex(db_path).index_markdown_tree(root)

    assert main(["search", "source-of-truth", "--db", str(db_path)]) == 0

    output = capsys.readouterr().out
    assert "ssot/truth.md [source_of_truth] Source Truth" in output


def test_init_creates_workspace_manifest_and_refuses_overwrite(tmp_path: Path):
    root = tmp_path / "team-memory"

    assert main(["init", str(root)]) == 0
    manifest = root / "antma.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data == {
        "format": "antma-workspace",
        "workspace_schema_version": 1,
        "canonical_ledger": "markdown",
    }

    manifest.write_text('{"custom": true}\n', encoding="utf-8")
    assert main(["init", str(root)]) == 0
    assert json.loads(manifest.read_text(encoding="utf-8")) == {"custom": True}

    assert main(["init", str(root), "--overwrite"]) == 0
    assert json.loads(manifest.read_text(encoding="utf-8"))["format"] == "antma-workspace"


def test_doctor_reports_healthy_workspace_and_index(tmp_path: Path, capsys):
    root = tmp_path / "team-memory"
    db_path = root / ".antma" / "index.db"
    assert main(["init", str(root)]) == 0
    assert main(["index", str(root), "--db", str(db_path)]) == 0

    assert main(["doctor", str(root), "--db", str(db_path)]) == 0

    output = capsys.readouterr().out
    assert "ANTMA doctor: healthy" in output


def test_doctor_reports_missing_workspace_manifest(tmp_path: Path, capsys):
    root = tmp_path / "team-memory"
    root.mkdir()
    db_path = root / ".antma" / "index.db"
    MemoryIndex(db_path).index_markdown_tree(root)

    assert main(["doctor", str(root), "--db", str(db_path)]) == 1

    output = capsys.readouterr().out
    assert "Workspace manifest is missing" in output


def test_doctor_reports_db_missing_metadata(tmp_path: Path, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    db_path = root / ".antma" / "index.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE VIRTUAL TABLE memories
            USING fts5(path, title, kind, body)
            """
        )

    assert main(["doctor", str(root), "--db", str(db_path)]) == 1

    output = capsys.readouterr().out
    assert "missing ANTMA metadata" in output


def test_doctor_reports_unsupported_index_schema(tmp_path: Path, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    db_path = root / ".antma" / "index.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
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

    assert main(["doctor", str(root), "--db", str(db_path)]) == 1

    output = capsys.readouterr().out
    assert "schema version '999' is not supported" in output


def test_search_missing_db_fails_without_creating_db(tmp_path: Path, capsys):
    db_path = tmp_path / "missing" / "index.db"

    assert main(["search", "launch", "--db", str(db_path)]) == 1

    captured = capsys.readouterr()
    assert "Index DB is missing" in captured.err
    assert "antma index PATH --db" in captured.err
    assert not db_path.exists()
