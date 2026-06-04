from pathlib import Path

from antma import AntmaProject
from antma.cli import main


def test_antma_project_create_review_promote_rollback_status(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    (root / "notes").mkdir()
    (root / "memory").mkdir()
    (root / "notes" / "today.md").write_text(
        "Brad prefers short Korean operating replies.\n",
        encoding="utf-8",
    )
    (root / "memory" / "project.md").write_text("# Project Memory\n", encoding="utf-8")
    project = AntmaProject.open(root)

    candidate = project.create_candidate(
        source="notes/today.md",
        destination="memory/project.md",
        summary="Korean replies",
        text="Brad prefers short Korean operating replies.",
        scope="project",
        risk="low",
        sensitivity="internal",
    )
    review_result = project.review.run(candidate_id=candidate.candidate_id)
    promotion = project.promote(candidate.candidate_id)
    rollback = project.rollback(promotion["results"][0]["promotion_id"])
    status = project.status()

    assert review_result[0]["to_status"] == "auto_passed"
    assert promotion["succeeded"] == 1
    assert rollback["status"] == "rolled_back"
    assert status["queues"]["rolled_back"] == 1


def test_antma_project_approvals_api(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    project = AntmaProject.open(root)
    candidate = project.create_candidate(
        source_type="manual",
        destination="memory/project.md",
        summary="Manual preference",
        text="Brad prefers concise Korean replies.",
        scope="project",
        risk="low",
        sensitivity="internal",
    )
    project.review.run(candidate_id=candidate.candidate_id)

    assert project.approvals.list()[0]["candidate_id"] == candidate.candidate_id
    held = project.approvals.hold(candidate.candidate_id, reason="needs confirmation")
    assert held["status"] == "held"
    edited = project.approvals.edit(
        candidate.candidate_id,
        proposed_text="Updated memory text.",
        scope="project",
        risk="medium",
        sensitivity="internal",
        destination="memory/project.md",
        supersedes=["entry_123"],
    )
    assert edited["status"] == "candidate"
    assert edited["review"]["edited"] is True
