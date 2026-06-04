import json
from pathlib import Path

from antma.candidates import create_candidate
from antma.cli import main


def test_review_run_moves_candidate_to_auto_passed(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    (root / "notes").mkdir()
    (root / "notes" / "today.md").write_text("Brad prefers short Korean replies.\n", encoding="utf-8")
    monkeypatch.chdir(root)
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
                "Brad prefers short Korean replies.",
                "--scope",
                "project",
                "--risk",
                "low",
                "--sensitivity",
                "internal",
            ]
        )
        == 0
    )
    candidate_id = capsys.readouterr().out.strip()

    assert main(["review", "run", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result[0]["candidate_id"] == candidate_id
    assert result[0]["from_status"] == "candidate"
    assert result[0]["to_status"] == "auto_passed"
    assert result[0]["reason_code"] == "low_risk_auto_allowed"
    assert not (root / ".antma" / "queue" / "candidates" / f"{candidate_id}.json").exists()
    assert (root / ".antma" / "queue" / "auto-passed" / f"{candidate_id}.json").exists()


def test_review_run_all_includes_blocked_candidate(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = create_candidate(
        root=root,
        source_type="manual",
        destination="memory/project.md",
        summary="Manual preference",
        text="Brad prefers concise Korean replies.",
        scope="project",
        risk="low",
        sensitivity="internal",
    )
    path = root / ".antma" / "queue" / "candidates" / f"{candidate.candidate_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "blocked"
    blocked = root / ".antma" / "queue" / "blocked" / f"{candidate.candidate_id}.json"
    blocked.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    path.unlink()
    capsys.readouterr()

    assert main(["review", "run", "--all", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result[0]["candidate_id"] == candidate.candidate_id
    assert result[0]["from_status"] == "blocked"
    assert result[0]["to_status"] == "manual_review"
    assert result[0]["reason_code"] == "source_hash_missing"


def test_review_run_without_all_only_reviews_pending_candidates(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = create_candidate(
        root=root,
        source_type="manual",
        destination="memory/project.md",
        summary="Manual preference",
        text="Brad prefers concise Korean replies.",
        scope="project",
        risk="low",
        sensitivity="internal",
    )
    path = root / ".antma" / "queue" / "candidates" / f"{candidate.candidate_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "blocked"
    blocked = root / ".antma" / "queue" / "blocked" / f"{candidate.candidate_id}.json"
    blocked.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    path.unlink()
    capsys.readouterr()

    assert main(["review", "run", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert blocked.exists()


def test_policy_validate_and_show(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    capsys.readouterr()

    assert main(["policy", "validate"]) == 0
    assert "Policy default: valid" in capsys.readouterr().out

    assert main(["policy", "show"]) == 0
    shown = capsys.readouterr().out
    assert 'name = "default"' in shown
    assert "lock_timeout_seconds = 10" in shown
