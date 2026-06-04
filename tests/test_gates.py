import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from antma.candidates import create_candidate, show_candidate
from antma.cli import main
from antma.gates import GateEngine
from antma.policy import load_project_policy


def init_root(tmp_path: Path) -> Path:
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    return root


def create_file_candidate(root: Path, **overrides):
    (root / "notes").mkdir(exist_ok=True)
    source = root / "notes" / "today.md"
    source.write_text("Brad prefers short Korean operating replies.\n", encoding="utf-8")
    params = {
        "root": root,
        "source": "notes/today.md",
        "source_type": "file",
        "destination": "memory/project.md",
        "summary": "Korean reply preference",
        "text": "Brad prefers short Korean operating replies.",
        "scope": "project",
        "risk": "low",
        "sensitivity": "internal",
    }
    params.update(overrides)
    return create_candidate(**params)


def evaluate(root: Path, candidate_id: str):
    policy = load_project_policy(root)
    return GateEngine(policy, root).evaluate(show_candidate(root, candidate_id))


def test_gate_low_risk_internal_project_auto_passed(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root)

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "auto_passed"
    assert result.reason_code == "low_risk_auto_allowed"
    assert result.next_action == "promote"


def test_gate_high_risk_manual_review(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root, risk="high")

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "manual_review"
    assert result.reason_code == "high_risk_requires_review"


def test_gate_secret_rejected(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root, sensitivity="secret")

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "rejected"
    assert result.reason_code == "secret_data_detected"


def test_gate_sensitive_manual_review_reason_code(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root, sensitivity="sensitive")

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "manual_review"
    assert result.reason_code == "sensitive_data_detected"


def test_gate_manual_source_require_source_hash_routes_source_hash_missing(tmp_path: Path):
    root = init_root(tmp_path)
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

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "manual_review"
    assert result.reason_code == "source_hash_missing"
    assert result.next_action == "manual_review"


def test_gate_missing_source_blocked(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root)
    (root / "notes" / "today.md").unlink()

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "blocked"
    assert result.reason_code == "source_missing"


def test_gate_hash_mismatch_blocked(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root)
    (root / "notes" / "today.md").write_text("Changed source.\n", encoding="utf-8")

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "blocked"
    assert result.reason_code == "source_hash_mismatch"


def test_gate_stale_source_manual_review(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root)
    old_time = datetime.now(timezone.utc) - timedelta(days=45)
    os.utime(root / "notes" / "today.md", (old_time.timestamp(), old_time.timestamp()))

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "manual_review"
    assert result.reason_code == "source_stale"


def test_gate_file_source_created_at_null_uses_mtime(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root)

    result = evaluate(root, candidate.candidate_id)

    assert show_candidate(root, candidate.candidate_id)["source"]["created_at"] is None
    assert result.status == "auto_passed"


def test_gate_manual_source_created_at_null_not_stale_by_created_at(tmp_path: Path):
    root = init_root(tmp_path)
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

    result = evaluate(root, candidate.candidate_id)

    assert result.reason_code == "source_hash_missing"
    assert result.reason_code != "source_stale"


def test_gate_external_source_blocked_by_default(tmp_path: Path):
    root = init_root(tmp_path)
    external = tmp_path / "external.md"
    external.write_text("External source.\n", encoding="utf-8")
    candidate = create_file_candidate(root, source=str(external))

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "blocked"
    assert result.reason_code == "source_outside_root"


def test_gate_destination_outside_root_blocked(tmp_path: Path):
    root = init_root(tmp_path)
    candidate = create_file_candidate(root)
    path = root / ".antma" / "queue" / "candidates" / f"{candidate.candidate_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["destination"]["path"] = "../outside.md"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "blocked"
    assert result.reason_code == "destination_outside_root"


def test_gate_conflict_manual_review(tmp_path: Path):
    root = init_root(tmp_path)
    (root / "memory").mkdir()
    (root / "memory" / "project.md").write_text(
        "# Project Memory\n\nBrad prefers long English operating replies.\n",
        encoding="utf-8",
    )
    candidate = create_file_candidate(root)

    result = evaluate(root, candidate.candidate_id)

    assert result.status == "manual_review"
    assert result.reason_code == "conflict_detected"
    assert result.conflicts


def test_conflict_manual_review_includes_context_excerpt(tmp_path: Path):
    root = init_root(tmp_path)
    (root / "memory").mkdir()
    (root / "memory" / "project.md").write_text(
        "# Project Memory\n\nBefore\nBrad prefers long English operating replies.\nAfter\n",
        encoding="utf-8",
    )
    candidate = create_file_candidate(root)

    result = evaluate(root, candidate.candidate_id)

    assert "Brad prefers long English" in result.conflicts[0]["excerpt"]


def test_lock_timeout_defaults_to_10_seconds(tmp_path: Path):
    root = init_root(tmp_path)
    policy = load_project_policy(root)

    assert policy["promotion"]["lock_timeout_seconds"] == 10
