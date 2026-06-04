"""ANTMA 0.2 filesystem candidate models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    AUTO_PASSED = "auto_passed"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    HELD = "held"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class ReasonCode(str, Enum):
    LOW_RISK_AUTO_ALLOWED = "low_risk_auto_allowed"
    HIGH_RISK_REQUIRES_REVIEW = "high_risk_requires_review"
    SCOPE_REQUIRES_REVIEW = "scope_requires_review"
    SENSITIVITY_REQUIRES_REVIEW = "sensitivity_requires_review"
    SENSITIVE_DATA_DETECTED = "sensitive_data_detected"
    CLASSIFIED_DATA_DETECTED = "secret_data_detected"
    CLASSIFIED_REJECTED = "secret_rejected"
    SOURCE_OUTSIDE_ROOT = "source_outside_root"
    SOURCE_HASH_MISMATCH = "source_hash_mismatch"
    SOURCE_STALE = "source_stale"
    SOURCE_FRESHNESS_UNKNOWN = "source_freshness_unknown"
    DESTINATION_OUTSIDE_ROOT = "destination_outside_root"
    DESTINATION_NOT_WRITABLE = "destination_not_writable"
    DESTINATION_MISSING = "destination_missing"
    CONFLICT_DETECTED = "conflict_detected"
    APPEND_ONLY_REQUIRED = "append_only_required"
    POLICY_INVALID = "policy_invalid"
    POLICY_NOT_FOUND = "policy_not_found"
    TEXT_TOO_LONG = "text_too_long"
    MANUAL_APPROVAL_REQUIRED = "manual_approval_required"
    MANUAL_APPROVED = "manual_approved"
    MANUAL_REJECTED = "manual_rejected"
    MANUAL_HELD = "manual_held"
    PROMOTION_WRITE_FAILED = "promotion_write_failed"
    SNAPSHOT_FAILED = "snapshot_failed"
    WRITE_CONFLICT = "write_conflict"
    EVIDENCE_MISSING = "evidence_missing"
    SOURCE_MISSING = "source_missing"
    SOURCE_HASH_MISSING = "source_hash_missing"
    INVALID_DESTINATION = "invalid_destination"


class Scope(str, Enum):
    PERSONAL = "personal"
    PROJECT = "project"
    SHARED = "shared"
    PERSONA = "persona"
    SSOT = "ssot"
    SECURITY = "security"


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CandidateSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class SourceKind(str, Enum):
    FILE = "file"
    MANUAL = "manual"
    MESSAGE = "message"
    API = "api"


@dataclass
class GateResult:
    status: str
    reason_code: str
    next_action: str
    messages: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "next_action": self.next_action,
            "messages": list(self.messages),
            "conflicts": list(self.conflicts),
        }


@dataclass
class CandidateSource:
    kind: str
    path: Optional[str]
    hash: Optional[str]
    created_at: Optional[str]
    observed_at: str
    locator: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "hash": self.hash,
            "created_at": self.created_at,
            "observed_at": self.observed_at,
            "locator": self.locator,
        }


@dataclass
class CandidateDestination:
    path: str
    section: Optional[str] = None
    mode: str = "append"

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "section": self.section, "mode": self.mode}


@dataclass
class CandidateEvidence:
    kind: str
    locator: str
    source_hash: Optional[str] = None
    quote: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "locator": self.locator,
            "source_hash": self.source_hash,
            "quote": self.quote,
        }


@dataclass
class CandidateReview:
    reviewer: Optional[str] = None
    decision: Optional[str] = None
    decision_at: Optional[str] = None
    reason: Optional[str] = None
    edited: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "decision": self.decision,
            "decision_at": self.decision_at,
            "reason": self.reason,
            "edited": self.edited,
        }


@dataclass
class Candidate:
    schema_version: str
    candidate_id: str
    created_at: str
    updated_at: str
    status: str
    reason_code: Optional[str]
    next_action: str
    summary: str
    text: str
    source: CandidateSource
    destination: CandidateDestination
    scope: str
    risk: str
    sensitivity: str
    evidence: List[CandidateEvidence]
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    supersedes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    review: CandidateReview = field(default_factory=CandidateReview)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "reason_code": self.reason_code,
            "next_action": self.next_action,
            "summary": self.summary,
            "text": self.text,
            "source": self.source.to_dict(),
            "destination": self.destination.to_dict(),
            "scope": self.scope,
            "risk": self.risk,
            "sensitivity": self.sensitivity,
            "evidence": [item.to_dict() for item in self.evidence],
            "conflicts": list(self.conflicts),
            "supersedes": list(self.supersedes),
            "metadata": dict(self.metadata),
            "review": self.review.to_dict(),
        }
