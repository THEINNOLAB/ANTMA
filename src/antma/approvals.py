"""Manual approval operations for ANTMA candidates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from antma.candidates import (
    CandidateError,
    find_candidate_file,
    iter_candidate_files,
    load_candidate,
    utc_now,
    write_candidate_data,
)
from antma.ledger import append_audit_event
from antma.models import CandidateSensitivity, CandidateStatus, ReasonCode, Risk, Scope


REVIEW_STATUSES = {CandidateStatus.MANUAL_REVIEW.value, CandidateStatus.HELD.value}


class ApprovalError(CandidateError):
    """Raised for invalid manual approval operations."""


def list_approvals(root: Path, status: Optional[str] = None) -> List[Dict[str, Any]]:
    root = root.resolve()
    if status is not None:
        CandidateStatus(status)
        statuses = (status,)
    else:
        statuses = (CandidateStatus.MANUAL_REVIEW.value, CandidateStatus.HELD.value)
    candidates: List[Dict[str, Any]] = []
    for candidate_status in statuses:
        for path in iter_candidate_files(root, status=candidate_status):
            candidates.append(load_candidate(path))
    return sorted(candidates, key=lambda item: (item.get("created_at", ""), item["candidate_id"]))


def show_approval(root: Path, candidate_id: str) -> Dict[str, Any]:
    data = load_candidate(find_candidate_file(root, candidate_id))
    if data["status"] not in REVIEW_STATUSES:
        raise ApprovalError(f"Candidate is not awaiting manual approval: {candidate_id}")
    return data


def approve_candidate(root: Path, candidate_id: str, reviewer: str = "local-user") -> Dict[str, Any]:
    return _decision(
        root,
        candidate_id,
        status=CandidateStatus.APPROVED.value,
        reason_code=ReasonCode.MANUAL_APPROVED.value,
        next_action="promote",
        decision="approved",
        reviewer=reviewer,
        reason=None,
        action="approvals.approve",
    )


def reject_candidate(root: Path, candidate_id: str, reason: str, reviewer: str = "local-user") -> Dict[str, Any]:
    if not reason.strip():
        raise ApprovalError("Reject reason is required.")
    return _decision(
        root,
        candidate_id,
        status=CandidateStatus.REJECTED.value,
        reason_code=ReasonCode.MANUAL_REJECTED.value,
        next_action="no_action",
        decision="rejected",
        reviewer=reviewer,
        reason=reason,
        action="approvals.reject",
    )


def hold_candidate(root: Path, candidate_id: str, reason: str, reviewer: str = "local-user") -> Dict[str, Any]:
    if not reason.strip():
        raise ApprovalError("Hold reason is required.")
    return _decision(
        root,
        candidate_id,
        status=CandidateStatus.HELD.value,
        reason_code=ReasonCode.MANUAL_HELD.value,
        next_action="manual_review",
        decision="held",
        reviewer=reviewer,
        reason=reason,
        action="approvals.hold",
    )


def edit_candidate(
    root: Path,
    candidate_id: str,
    proposed_text: Optional[str] = None,
    scope: Optional[str] = None,
    risk: Optional[str] = None,
    sensitivity: Optional[str] = None,
    destination: Optional[str] = None,
    supersedes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    root = root.resolve()
    path = find_candidate_file(root, candidate_id)
    data = load_candidate(path)
    _require_review_status(data)
    from_status = data["status"]

    material = False
    if proposed_text is not None:
        if not proposed_text.strip():
            raise ApprovalError("Edited text must be non-empty.")
        data["text"] = proposed_text
        material = True
    if scope is not None:
        data["scope"] = Scope(scope).value
        material = True
    if risk is not None:
        data["risk"] = Risk(risk).value
        material = True
    if sensitivity is not None:
        data["sensitivity"] = CandidateSensitivity(sensitivity).value
        material = True
    if destination is not None:
        data["destination"]["path"] = destination
        material = True
    if supersedes is not None:
        data["supersedes"] = list(supersedes)
        material = True

    data["updated_at"] = utc_now()
    if material:
        review = data["review"]
        review["reviewer"] = None
        review["decision"] = None
        review["decision_at"] = None
        review["reason"] = None
        review["edited"] = True
        data["status"] = CandidateStatus.CANDIDATE.value
        data["reason_code"] = None
        data["next_action"] = "review"

    write_candidate_data(root, data, old_path=path, validate_root=True)
    append_audit_event(
        root,
        "approvals.edit",
        candidate_id=candidate_id,
        from_status=from_status,
        to_status=data["status"],
        actor="antma-cli",
        material=material,
    )
    return data


def _decision(
    root: Path,
    candidate_id: str,
    status: str,
    reason_code: str,
    next_action: str,
    decision: str,
    reviewer: str,
    reason: Optional[str],
    action: str,
) -> Dict[str, Any]:
    root = root.resolve()
    path = find_candidate_file(root, candidate_id)
    data = load_candidate(path)
    _require_review_status(data)
    from_status = data["status"]
    now = utc_now()
    data["status"] = status
    data["reason_code"] = reason_code
    data["next_action"] = next_action
    data["updated_at"] = now
    data["review"]["reviewer"] = reviewer
    data["review"]["decision"] = decision
    data["review"]["decision_at"] = now
    data["review"]["reason"] = reason
    write_candidate_data(root, data, old_path=path, validate_root=False)
    append_audit_event(
        root,
        action,
        candidate_id=candidate_id,
        from_status=from_status,
        to_status=status,
        reason_code=reason_code,
        actor=reviewer,
        reason=reason,
    )
    return data


def _require_review_status(data: Dict[str, Any]) -> None:
    if data["status"] not in REVIEW_STATUSES:
        raise ApprovalError(
            f"Candidate status must be manual_review or held, got {data['status']}: {data['candidate_id']}"
        )
