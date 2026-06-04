import json
import os
from pathlib import Path

from antma.candidates import create_candidate, show_candidate
from antma.cli import main
from antma.executor import can_break_lock
from antma.review import run_review


def auto_candidate(root: Path):
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
    return candidate


def test_promotion_appends_marker_block(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = auto_candidate(root)
    capsys.readouterr()

    assert main(["promote", "run", candidate.candidate_id]) == 0

    destination = (root / "memory" / "project.md").read_text(encoding="utf-8")
    assert "# Project Memory\n" in destination
    assert "<!-- antma:promotion" in destination
    assert f'candidate="{candidate.candidate_id}"' in destination
    assert "Brad prefers short Korean operating replies." in destination
    assert show_candidate(root, candidate.candidate_id)["status"] == "promoted"


def test_promotion_writes_audit_and_promotion_ledgers(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = auto_candidate(root)
    capsys.readouterr()

    assert main(["promote", "run", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)

    promotion_id = result["results"][0]["promotion_id"]
    audit = (root / ".antma" / "ledger" / "audit.jsonl").read_text(encoding="utf-8")
    promotions = (root / ".antma" / "ledger" / "promotions.jsonl").read_text(encoding="utf-8")
    assert "promotion.run" in audit
    assert promotion_id in promotions
    assert candidate.candidate_id in promotions


def test_promotion_creates_snapshot_manifest(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = auto_candidate(root)
    capsys.readouterr()

    assert main(["promote", "run", "--json"]) == 0
    promotion_id = json.loads(capsys.readouterr().out)["results"][0]["promotion_id"]
    manifest = json.loads(
        (root / ".antma" / "snapshots" / promotion_id / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["promotion_id"] == promotion_id
    assert manifest["candidate_id"] == candidate.candidate_id
    assert manifest["destination"] == "memory/project.md"
    assert (root / ".antma" / "snapshots" / promotion_id / "before" / "memory" / "project.md").exists()
    assert (root / ".antma" / "snapshots" / promotion_id / "after" / "memory" / "project.md").exists()


def test_promotion_records_destination_hash_before_after(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    auto_candidate(root)
    capsys.readouterr()

    assert main(["promote", "run", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)["results"][0]

    assert result["destination_hash_before"].startswith("sha256:")
    assert result["destination_hash_after"].startswith("sha256:")
    assert result["destination_hash_before"] != result["destination_hash_after"]


def test_promote_run_dry_run_does_not_write_destination(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    auto_candidate(root)
    before = (root / "memory" / "project.md").read_text(encoding="utf-8")
    capsys.readouterr()

    assert main(["promote", "run", "--dry-run", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["results"][0]["status"] == "dry_run"
    assert (root / "memory" / "project.md").read_text(encoding="utf-8") == before


def test_status_json_counts_queues(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    auto_candidate(root)
    capsys.readouterr()

    assert main(["status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)

    assert status["queues"]["auto_passed"] == 1
    assert status["queues"]["candidate"] == 0


def test_ledger_show_candidate_lookup(tmp_path: Path, monkeypatch, capsys):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0
    monkeypatch.chdir(root)
    candidate = auto_candidate(root)
    capsys.readouterr()

    assert main(["ledger", "show", "--type", "audit", "--candidate", candidate.candidate_id]) == 0
    output = capsys.readouterr().out

    assert "candidate.create" in output
    assert candidate.candidate_id in output


def test_destination_lock_payload_and_stale_lock_rules(tmp_path: Path):
    lock = tmp_path / "destination.lock"
    lock.write_text(
        json.dumps(
            {
                "pid": 99999999,
                "created_at": "2000-01-01T00:00:00+00:00",
                "destination": "memory/project.md",
                "candidate_id": "cand_20260604_072000_4f2a",
            }
        ),
        encoding="utf-8",
    )

    assert can_break_lock(lock, timeout_seconds=10)
    lock.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "created_at": "2000-01-01T00:00:00+00:00",
                "destination": "memory/project.md",
                "candidate_id": "cand_20260604_072000_4f2a",
            }
        ),
        encoding="utf-8",
    )
    assert not can_break_lock(lock, timeout_seconds=10)
