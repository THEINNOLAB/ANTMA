import json
from pathlib import Path

from antma.cli import main


def create_source_candidate(root: Path, capsys):
    capsys.readouterr()
    (root / "notes").mkdir()
    (root / "notes" / "today.md").write_text(
        "Brad prefers short Korean operating replies.\n",
        encoding="utf-8",
    )
    result = main(
        [
            "candidate",
            "create",
            "--source",
            "notes/today.md",
            "--source-type",
            "file",
            "--destination",
            "memory/project.md",
            "--summary",
            "Korean operating reply preference",
            "--text",
            "Brad prefers short Korean operating replies.",
            "--scope",
            "project",
            "--risk",
            "low",
            "--sensitivity",
            "internal",
        ]
    )
    captured = capsys.readouterr()
    return result, captured.out.strip()


def test_candidate_create_writes_json(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    capsys.readouterr()
    monkeypatch.chdir(root)

    result, candidate_id = create_source_candidate(root, capsys)

    assert result == 0
    path = root / ".antma" / "queue" / "candidates" / f"{candidate_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.2"
    assert data["candidate_id"] == candidate_id
    assert data["status"] == "candidate"
    assert data["next_action"] == "review"
    assert data["source"]["kind"] == "file"
    assert data["source"]["path"] == "notes/today.md"
    assert data["source"]["hash"].startswith("sha256:")
    assert data["destination"]["path"] == "memory/project.md"
    assert data["evidence"][0]["locator"] == "notes/today.md"
    assert data["evidence"][0]["source_hash"] == data["source"]["hash"]


def test_candidate_create_manual_source_text_only(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    capsys.readouterr()
    monkeypatch.chdir(root)

    result = main(
        [
            "candidate",
            "create",
            "--source-type",
            "manual",
            "--destination",
            "memory/project.md",
            "--summary",
            "Korean replies",
            "--text",
            "Brad prefers short Korean operating replies.",
            "--scope",
            "project",
            "--risk",
            "low",
            "--sensitivity",
            "internal",
        ]
    )
    candidate_id = capsys.readouterr().out.strip()

    assert result == 0
    data = json.loads(
        (root / ".antma" / "queue" / "candidates" / f"{candidate_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["source"] == {
        "kind": "manual",
        "path": None,
        "hash": None,
        "created_at": None,
        "observed_at": data["source"]["observed_at"],
        "locator": "manual:local-user",
    }
    assert data["evidence"][0]["kind"] == "manual"
    assert data["evidence"][0]["locator"] == "manual:local-user"


def test_candidate_create_supersedes(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    capsys.readouterr()
    monkeypatch.chdir(root)

    result = main(
        [
            "candidate",
            "create",
            "--source-type",
            "manual",
            "--destination",
            "memory/project.md",
            "--summary",
            "Updated preference",
            "--text",
            "Use concise Korean operating replies.",
            "--scope",
            "project",
            "--risk",
            "medium",
            "--sensitivity",
            "internal",
            "--supersedes",
            "entry_123",
            "--supersedes",
            "cand_20260604_072000_4f2a",
        ]
    )
    candidate_id = capsys.readouterr().out.strip()

    assert result == 0
    data = json.loads(
        (root / ".antma" / "queue" / "candidates" / f"{candidate_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["supersedes"] == ["entry_123", "cand_20260604_072000_4f2a"]


def test_candidate_list_show_and_status_filter(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    result, candidate_id = create_source_candidate(root, capsys)
    assert result == 0

    assert main(["candidate", "list", "--status", "candidate"]) == 0
    list_output = capsys.readouterr().out
    assert candidate_id in list_output
    assert "Korean operating reply preference" in list_output

    assert main(["candidate", "show", candidate_id]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["candidate_id"] == candidate_id
    assert shown["summary"] == "Korean operating reply preference"


def test_candidate_delete_unpromoted_only(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    result, candidate_id = create_source_candidate(root, capsys)
    assert result == 0

    assert main(["candidate", "delete", candidate_id, "--reason", "test cleanup"]) == 0

    assert not (root / ".antma" / "queue" / "candidates" / f"{candidate_id}.json").exists()
    audit = (root / ".antma" / "ledger" / "audit.jsonl").read_text(encoding="utf-8")
    assert '"action": "candidate.delete"' in audit
    assert f'"candidate_id": "{candidate_id}"' in audit


def test_candidate_delete_rejects_promoted_candidate(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    result, candidate_id = create_source_candidate(root, capsys)
    assert result == 0

    original = root / ".antma" / "queue" / "candidates" / f"{candidate_id}.json"
    data = json.loads(original.read_text(encoding="utf-8"))
    data["status"] = "promoted"
    promoted = root / ".antma" / "queue" / "promoted" / f"{candidate_id}.json"
    promoted.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    original.unlink()

    assert main(["candidate", "delete", candidate_id]) == 1
    assert promoted.exists()


def test_candidate_schema_requires_non_empty_text(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    capsys.readouterr()
    monkeypatch.chdir(root)

    result = main(
        [
            "candidate",
            "create",
            "--source-type",
            "manual",
            "--destination",
            "memory/project.md",
            "--summary",
            "Missing text",
            "--text",
            "",
            "--scope",
            "project",
            "--risk",
            "low",
            "--sensitivity",
            "internal",
        ]
    )

    assert result == 1
    captured = capsys.readouterr()
    assert "text must be non-empty" in captured.err
    assert not list((root / ".antma" / "queue" / "candidates").glob("*.json"))
