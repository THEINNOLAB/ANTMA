import json
from pathlib import Path

from antma.candidates import create_candidate
from antma.cli import main
from antma.ledger import read_jsonl
from antma.review import run_review


def promoted_candidate(root: Path, monkeypatch, capsys):
    (root / "notes").mkdir(exist_ok=True)
    (root / "memory").mkdir(exist_ok=True)
    (root / "notes" / "today.md").write_text(
        "Brad prefers short Korean operating replies.\n",
        encoding="utf-8",
    )
    (root / "memory" / "project.md").write_text("# Project Memory\n", encoding="utf-8")
    candidate = create_candidate(
        root=root,
        source="notes/today.md",
        source_type="file",
        destination="memory/project.md",
        summary="Korean replies",
        text="Brad prefers short Korean operating replies.",
        scope="project",
        risk="low",
        sensitivity="internal",
    )
    result = run_review(root, candidate_id=candidate.candidate_id)
    assert result[0]["to_status"] == "auto_passed"
    monkeypatch.chdir(root)
    capsys.readouterr()
    assert main(["promote", "run", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    return candidate, output["results"][0]["promotion_id"]


def test_rollback_removes_marker_block(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    candidate, promotion_id = promoted_candidate(root, monkeypatch, capsys)

    assert main(["rollback", promotion_id, "--json"]) == 0
    result = json.loads(capsys.readouterr().out)

    destination = (root / "memory" / "project.md").read_text(encoding="utf-8")
    assert result["status"] == "rolled_back"
    assert result["candidate_id"] == candidate.candidate_id
    assert "<!-- antma:promotion" not in destination
    assert "Brad prefers short Korean operating replies." not in destination
    assert (root / ".antma" / "queue" / "rolled-back" / f"{candidate.candidate_id}.json").exists()


def test_rollback_detects_destination_hash_after_write_conflict(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    _candidate, promotion_id = promoted_candidate(root, monkeypatch, capsys)
    destination = root / "memory" / "project.md"
    destination.write_text(destination.read_text(encoding="utf-8") + "\nManual edit.\n", encoding="utf-8")

    assert main(["rollback", promotion_id, "--json"]) == 1
    result = json.loads(capsys.readouterr().out)

    assert result["status"] == "failed"
    assert result["reason_code"] == "write_conflict"
    assert "<!-- antma:promotion" in destination.read_text(encoding="utf-8")


def test_rollback_dry_run_does_not_modify_destination(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    _candidate, promotion_id = promoted_candidate(root, monkeypatch, capsys)
    destination = root / "memory" / "project.md"
    before = destination.read_text(encoding="utf-8")

    assert main(["rollback", promotion_id, "--dry-run", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["status"] == "dry_run"
    assert destination.read_text(encoding="utf-8") == before


def test_end_to_end_auto_promotion_and_rollback(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    (root / "notes").mkdir()
    (root / "memory").mkdir()
    (root / "notes" / "today.md").write_text(
        "Brad prefers short Korean operating replies.\n",
        encoding="utf-8",
    )
    (root / "memory" / "project.md").write_text("# Project Memory\n", encoding="utf-8")
    capsys.readouterr()

    assert (
        main(
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
                "Korean replies",
                "--text",
                "Brad prefers short Korean operating replies.",
                "--scope",
                "project",
                "--risk",
                "low",
                "--sensitivity",
                "internal",
                "--evidence",
                "notes/today.md",
            ]
        )
        == 0
    )
    candidate_id = capsys.readouterr().out.strip()

    assert main(["review", "run", "--all"]) == 0
    capsys.readouterr()
    assert (root / ".antma" / "queue" / "auto-passed" / f"{candidate_id}.json").exists()

    assert main(["promote", "run", "--json"]) == 0
    promotion_id = json.loads(capsys.readouterr().out)["results"][0]["promotion_id"]
    destination = (root / "memory" / "project.md").read_text(encoding="utf-8")
    assert "<!-- antma:promotion" in destination
    assert "Brad prefers short Korean operating replies." in destination
    assert read_jsonl(root / ".antma" / "ledger" / "audit.jsonl")
    assert read_jsonl(root / ".antma" / "ledger" / "promotions.jsonl")

    assert main(["rollback", promotion_id]) == 0
    assert "<!-- antma:promotion" not in (root / "memory" / "project.md").read_text(
        encoding="utf-8"
    )
