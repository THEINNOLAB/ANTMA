"""High-level ANTMA 0.2 project API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from antma.approvals import (
    approve_candidate,
    edit_candidate,
    hold_candidate,
    list_approvals,
    reject_candidate,
    show_approval,
)
from antma.candidates import create_candidate
from antma.executor import run_promotions
from antma.rollback import rollback_promotion
from antma.review import run_review
from antma.status import project_status


class AntmaProject:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.review = ReviewManager(self)
        self.approvals = ApprovalManager(self)

    @classmethod
    def open(cls, root: Union[str, Path] = ".") -> "AntmaProject":
        return cls(Path(root))

    def create_candidate(
        self,
        destination: str,
        summary: str,
        text: str,
        scope: str,
        risk: str,
        sensitivity: str,
        source: Optional[str] = None,
        source_type: str = "file",
        supersedes: Optional[Sequence[str]] = None,
        evidence: Optional[Sequence[str]] = None,
    ):
        return create_candidate(
            root=self.root,
            source=source,
            source_type=source_type,
            destination=destination,
            summary=summary,
            text=text,
            scope=scope,
            risk=risk,
            sensitivity=sensitivity,
            supersedes=supersedes,
            evidence_values=evidence,
        )

    def promote(self, candidate_id: Optional[str] = None) -> Dict[str, Any]:
        return run_promotions(self.root, candidate_id=candidate_id)

    def rollback(self, promotion_id: str) -> Dict[str, Any]:
        return rollback_promotion(self.root, promotion_id)

    def status(self) -> Dict[str, object]:
        return project_status(self.root)


class ReviewManager:
    def __init__(self, project: AntmaProject):
        self.project = project

    def run(
        self,
        candidate_id: Optional[str] = None,
        run_all: bool = False,
        policy_name: str = "default",
    ) -> List[Dict[str, Any]]:
        return run_review(
            self.project.root,
            candidate_id=candidate_id,
            run_all=run_all,
            policy_name=policy_name,
        )


class ApprovalManager:
    def __init__(self, project: AntmaProject):
        self.project = project

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return list_approvals(self.project.root, status=status)

    def show(self, candidate_id: str) -> Dict[str, Any]:
        return show_approval(self.project.root, candidate_id)

    def approve(self, candidate_id: str, reviewer: str = "local-user") -> Dict[str, Any]:
        return approve_candidate(self.project.root, candidate_id, reviewer=reviewer)

    def reject(self, candidate_id: str, reason: str) -> Dict[str, Any]:
        return reject_candidate(self.project.root, candidate_id, reason=reason)

    def hold(self, candidate_id: str, reason: str) -> Dict[str, Any]:
        return hold_candidate(self.project.root, candidate_id, reason=reason)

    def edit(
        self,
        candidate_id: str,
        proposed_text: Optional[str] = None,
        scope: Optional[str] = None,
        risk: Optional[str] = None,
        sensitivity: Optional[str] = None,
        destination: Optional[str] = None,
        supersedes: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        return edit_candidate(
            self.project.root,
            candidate_id,
            proposed_text=proposed_text,
            scope=scope,
            risk=risk,
            sensitivity=sensitivity,
            destination=destination,
            supersedes=supersedes,
        )
