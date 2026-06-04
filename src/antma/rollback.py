"""Rollback promoted marker blocks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from antma.candidates import find_candidate_file, load_candidate, utc_now, write_candidate_data
from antma.fs import atomic_write_text, resolve_destination, sha256_text
from antma.ledger import append_audit_event, read_jsonl
from antma.models import CandidateStatus, ReasonCode


class RollbackError(ValueError):
    """Raised when rollback cannot be applied."""


def rollback_promotion(root: Path, promotion_id: str, dry_run: bool = False) -> Dict[str, Any]:
    root = root.resolve()
    promotion = find_promotion(root, promotion_id)
    candidate_id = promotion["candidate_id"]
    destination = resolve_destination(root, promotion["destination"])
    current_text = destination.read_text(encoding="utf-8") if destination.exists() else ""
    current_hash = sha256_text(current_text)
    expected_hash = promotion["destination_hash_after"]
    if current_hash != expected_hash:
        return {
            "promotion_id": promotion_id,
            "candidate_id": candidate_id,
            "destination": promotion["destination"],
            "status": "failed",
            "reason_code": ReasonCode.WRITE_CONFLICT.value,
            "destination_hash_before": current_hash,
            "destination_hash_after": current_hash,
        }

    updated_text = remove_marker_block(current_text, promotion_id, candidate_id)
    destination_hash_after = sha256_text(updated_text)
    result = {
        "promotion_id": promotion_id,
        "candidate_id": candidate_id,
        "destination": promotion["destination"],
        "status": "dry_run" if dry_run else "rolled_back",
        "reason_code": None if dry_run else "rolled_back",
        "destination_hash_before": current_hash,
        "destination_hash_after": destination_hash_after,
    }
    if dry_run:
        return result

    atomic_write_text(destination, updated_text, tmp_dir=root / ".antma" / "tmp")
    move_candidate_to_rolled_back(root, candidate_id, promotion_id)
    append_audit_event(
        root,
        "rollback.run",
        promotion_id=promotion_id,
        candidate_id=candidate_id,
        destination=promotion["destination"],
        reason_code="rolled_back",
        actor="antma-cli",
    )
    return result


def find_promotion(root: Path, promotion_id: str) -> Dict[str, Any]:
    for record in read_jsonl(root / ".antma" / "ledger" / "promotions.jsonl"):
        if record.get("promotion_id") == promotion_id:
            return record
    raise RollbackError(f"Promotion not found: {promotion_id}")


def remove_marker_block(text: str, promotion_id: str, candidate_id: str) -> str:
    pattern = re.compile(
        r"\n{0,2}<!-- antma:promotion id=\""
        + re.escape(promotion_id)
        + r"\" candidate=\""
        + re.escape(candidate_id)
        + r"\" started -->.*?<!-- antma:promotion id=\""
        + re.escape(promotion_id)
        + r"\" candidate=\""
        + re.escape(candidate_id)
        + r"\" ended -->\n?",
        re.DOTALL,
    )
    updated, count = pattern.subn("\n", text, count=1)
    if count != 1:
        raise RollbackError(f"Promotion marker block not found: {promotion_id}")
    return updated


def move_candidate_to_rolled_back(root: Path, candidate_id: str, promotion_id: str) -> None:
    path = find_candidate_file(root, candidate_id)
    data = load_candidate(path)
    data["status"] = CandidateStatus.ROLLED_BACK.value
    data["reason_code"] = "rolled_back"
    data["next_action"] = "no_action"
    data["updated_at"] = utc_now()
    data.setdefault("metadata", {})["rolled_back_promotion_id"] = promotion_id
    write_candidate_data(root, data, old_path=path, validate_root=False)
