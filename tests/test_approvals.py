import json
from pathlib import Path

from antma.approvals import approve_candidate, edit_candidate, hold_candidate, reject_candidate
from antma.candidates import create_candidate, show_candidate
from antma.cli import main
from antma.review import run_review


def manual_review_candidate(root: Path):
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
    result = run_review(root, candidate_id=candidate.candidate_id)
    assert result[0]["to_status"] == "manual_review"
    return candidate


def test_approval_approve_moves_candidate(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    candidate = manual_review_candidate(root)

    approved = approve_candidate(root, candidate.candidate_id, reviewer="reviewer")

    assert approved["status"] == "approved"
    assert approved["reason_code"] == "manual_approved"
    assert approved["next_action"] == "promote"
    assert approved["review"]["reviewer"] == "reviewer"
    assert (root / ".antma" / "queue" / "approved" / f"{candidate.candidate_id}.json").exists()


def test_approval_reject_records_reason(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    candidate = manual_review_candidate(root)

    rejected = reject_candidate(root, candidate.candidate_id, reason="source insufficient")

    assert rejected["status"] == "rejected"
    assert rejected["reason_code"] == "manual_rejected"
    assert rejected["review"]["reason"] == "source insufficient"
    audit = (root / ".antma" / "ledger" / "audit.jsonl").read_text(encoding="utf-8")
    assert "approvals.reject" in audit
    assert "source insufficient" in audit


def test_approval_hold_moves_candidate_to_held(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    candidate = manual_review_candidate(root)

    held = hold_candidate(root, candidate.candidate_id, reason="needs confirmation")

    assert held["status"] == "held"
    assert held["reason_code"] == "manual_held"
    assert held["next_action"] == "manual_review"
    assert (root / ".antma" / "queue" / "held" / f"{candidate.candidate_id}.json").exists()


def test_approval_approve_from_held_candidate(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    candidate = manual_review_candidate(root)
    hold_candidate(root, candidate.candidate_id, reason="needs confirmation")

    approved = approve_candidate(root, candidate.candidate_id)

    assert approved["status"] == "approved"
    assert not (root / ".antma" / "queue" / "held" / f"{candidate.candidate_id}.json").exists()
    assert (root / ".antma" / "queue" / "approved" / f"{candidate.candidate_id}.json").exists()


def test_approval_edit_material_change_invalidates_gate_decision(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    candidate = manual_review_candidate(root)
    approve_candidate(root, candidate.candidate_id, reviewer="reviewer")
    path = root / ".antma" / "queue" / "approved" / f"{candidate.candidate_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "manual_review"
    manual = root / ".antma" / "queue" / "manual-review" / f"{candidate.candidate_id}.json"
    manual.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    path.unlink()

    edited = edit_candidate(
        root,
        candidate.candidate_id,
        proposed_text="Brad prefers concise Korean operating replies.",
        scope="project",
        risk="medium",
        sensitivity="internal",
        destination="memory/project.md",
        supersedes=["entry_123"],
    )

    assert edited["status"] == "candidate"
    assert edited["reason_code"] is None
    assert edited["next_action"] == "review"
    assert edited["review"] == {
        "reviewer": None,
        "decision": None,
        "decision_at": None,
        "reason": None,
        "edited": True,
    }
    assert edited["text"] == "Brad prefers concise Korean operating replies."
    assert edited["risk"] == "medium"
    assert edited["supersedes"] == ["entry_123"]
    assert (root / ".antma" / "queue" / "candidates" / f"{candidate.candidate_id}.json").exists()


def test_approvals_cli_list_show_approve(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = manual_review_candidate(root)
    capsys.readouterr()

    assert main(["approvals", "list"]) == 0
    assert candidate.candidate_id in capsys.readouterr().out

    assert main(["approvals", "show", candidate.candidate_id]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["candidate_id"] == candidate.candidate_id

    assert main(["approvals", "approve", candidate.candidate_id]) == 0
    assert "Approved" in capsys.readouterr().out
    assert show_candidate(root, candidate.candidate_id)["status"] == "approved"


def test_approvals_cli_edit_material_change(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = manual_review_candidate(root)
    capsys.readouterr()

    assert (
        main(
            [
                "approvals",
                "edit",
                candidate.candidate_id,
                "--text",
                "Updated memory text.",
                "--scope",
                "project",
                "--risk",
                "medium",
                "--sensitivity",
                "internal",
                "--destination",
                "memory/project.md",
                "--supersedes",
                "entry_123",
            ]
        )
        == 0
    )

    assert "Edited" in capsys.readouterr().out
    data = show_candidate(root, candidate.candidate_id)
    assert data["status"] == "candidate"
    assert data["text"] == "Updated memory text."
    assert data["supersedes"] == ["entry_123"]
