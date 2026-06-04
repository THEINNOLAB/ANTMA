"""Candidate queue storage for ANTMA 0.2."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from antma.fs import PathValidationError, resolve_destination, sha256_file
from antma.ids import new_candidate_id
from antma.ledger import append_audit_event
from antma.models import (
    Candidate,
    CandidateDestination,
    CandidateEvidence,
    CandidateReview,
    CandidateSensitivity,
    CandidateSource,
    CandidateStatus,
    GateResult,
    Risk,
    Scope,
    SourceKind,
)


SCHEMA_VERSION = "0.2"
CANDIDATE_ID_RE = re.compile(r"^cand_\d{8}_\d{6}_[0-9a-f]+$")

QUEUE_DIR_BY_STATUS = {
    CandidateStatus.CANDIDATE.value: "candidates",
    CandidateStatus.AUTO_PASSED.value: "auto-passed",
    CandidateStatus.MANUAL_REVIEW.value: "manual-review",
    CandidateStatus.APPROVED.value: "approved",
    CandidateStatus.HELD.value: "held",
    CandidateStatus.BLOCKED.value: "blocked",
    CandidateStatus.REJECTED.value: "rejected",
    CandidateStatus.PROMOTED.value: "promoted",
    CandidateStatus.ROLLED_BACK.value: "rolled-back",
    CandidateStatus.FAILED.value: "failed",
}

STATUS_BY_QUEUE_DIR = {value: key for key, value in QUEUE_DIR_BY_STATUS.items()}
DELETABLE_STATUSES = {
    CandidateStatus.CANDIDATE.value,
    CandidateStatus.AUTO_PASSED.value,
    CandidateStatus.MANUAL_REVIEW.value,
    CandidateStatus.APPROVED.value,
    CandidateStatus.HELD.value,
    CandidateStatus.BLOCKED.value,
    CandidateStatus.REJECTED.value,
    CandidateStatus.FAILED.value,
}
REVIEWABLE_ALL_STATUSES = (
    CandidateStatus.CANDIDATE.value,
    CandidateStatus.BLOCKED.value,
    CandidateStatus.MANUAL_REVIEW.value,
    CandidateStatus.HELD.value,
)


class CandidateError(ValueError):
    """Raised for candidate queue errors."""


class CandidateValidationError(CandidateError):
    """Raised when candidate data does not satisfy the 0.2 schema."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def discover_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".antma" / "config.toml").exists() or (candidate / ".antma").is_dir():
            return candidate
    return current


def ensure_antma_state(root: Path) -> None:
    if not (root / ".antma").is_dir():
        raise CandidateError(f"ANTMA state not found at {root / '.antma'}. Run: antma init {root}")


def queue_path(root: Path, status: str) -> Path:
    try:
        directory = QUEUE_DIR_BY_STATUS[status]
    except KeyError as error:
        raise CandidateValidationError(f"Unknown candidate status: {status}") from error
    return root / ".antma" / "queue" / directory


def candidate_path(root: Path, candidate_id: str, status: str) -> Path:
    return queue_path(root, status) / f"{candidate_id}.json"


def create_candidate(
    root: Path,
    source_type: str,
    destination: str,
    summary: str,
    text: str,
    scope: str,
    risk: str,
    sensitivity: str,
    source: Optional[str] = None,
    supersedes: Optional[Sequence[str]] = None,
    evidence_values: Optional[Sequence[str]] = None,
) -> Candidate:
    root = root.resolve()
    ensure_antma_state(root)
    now = utc_now()
    source_kind = SourceKind(source_type).value
    source_path: Optional[str] = None
    source_hash: Optional[str] = None
    source_locator = "manual:local-user"

    if source_kind == SourceKind.FILE.value:
        if not source:
            raise CandidateValidationError("file source requires --source.")
        raw_source = Path(source)
        resolved_source = raw_source if raw_source.is_absolute() else root / raw_source
        if not resolved_source.is_file():
            raise CandidateValidationError(f"Source file not found: {source}")
        try:
            source_path = str(resolved_source.resolve().relative_to(root))
        except ValueError:
            source_path = str(resolved_source.resolve())
        source_hash = sha256_file(resolved_source)
        source_locator = source_path
    elif source:
        source_locator = source

    candidate = Candidate(
        schema_version=SCHEMA_VERSION,
        candidate_id=new_candidate_id(),
        created_at=now,
        updated_at=now,
        status=CandidateStatus.CANDIDATE.value,
        reason_code=None,
        next_action="review",
        summary=summary,
        text=text,
        source=CandidateSource(
            kind=source_kind,
            path=source_path,
            hash=source_hash,
            created_at=None,
            observed_at=now,
            locator=source_locator,
        ),
        destination=CandidateDestination(path=destination),
        scope=Scope(scope).value,
        risk=Risk(risk).value,
        sensitivity=CandidateSensitivity(sensitivity).value,
        evidence=build_evidence(
            source_kind=source_kind,
            source_locator=source_locator,
            source_hash=source_hash,
            summary=summary,
            text=text,
            evidence_values=evidence_values or (),
        ),
        conflicts=[],
        supersedes=list(supersedes or ()),
        metadata={"creator": "antma-cli", "tags": [], "policy": "default"},
        review=CandidateReview(),
    )
    validate_candidate(candidate.to_dict(), root=root)
    write_candidate(root, candidate)
    append_audit_event(
        root,
        "candidate.create",
        candidate_id=candidate.candidate_id,
        status=candidate.status,
        actor="antma-cli",
    )
    return candidate


def build_evidence(
    source_kind: str,
    source_locator: str,
    source_hash: Optional[str],
    summary: str,
    text: str,
    evidence_values: Sequence[str],
) -> List[CandidateEvidence]:
    if evidence_values:
        return [
            CandidateEvidence(
                kind=source_kind,
                locator=value,
                source_hash=source_hash,
                quote=None,
            )
            for value in evidence_values
        ]
    if source_kind == SourceKind.FILE.value:
        return [
            CandidateEvidence(
                kind=SourceKind.FILE.value,
                locator=source_locator,
                source_hash=source_hash,
                quote=None,
            )
        ]
    return [
        CandidateEvidence(
            kind=source_kind,
            locator=source_locator,
            source_hash=None,
            quote=summary or text,
        )
    ]


def write_candidate(root: Path, candidate: Candidate) -> Path:
    path = candidate_path(root, candidate.candidate_id, candidate.status)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(candidate.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_candidate(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_candidate_files(root: Path, status: Optional[str] = None) -> Iterable[Path]:
    statuses = [status] if status else list(QUEUE_DIR_BY_STATUS)
    for candidate_status in statuses:
        directory = queue_path(root, candidate_status)
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            yield path


def list_candidates(root: Path, status: Optional[str] = None) -> List[Dict[str, Any]]:
    root = root.resolve()
    ensure_antma_state(root)
    if status is not None:
        CandidateStatus(status)
    return [load_candidate(path) for path in iter_candidate_files(root, status=status)]


def candidate_files_for_review(
    root: Path,
    candidate_id: Optional[str] = None,
    run_all: bool = False,
) -> List[Path]:
    root = root.resolve()
    ensure_antma_state(root)
    if candidate_id:
        return [find_candidate_file(root, candidate_id)]
    statuses = REVIEWABLE_ALL_STATUSES if run_all else (CandidateStatus.CANDIDATE.value,)
    files: List[Path] = []
    for status in statuses:
        files.extend(iter_candidate_files(root, status=status))
    return sorted(files, key=lambda path: (load_candidate(path).get("created_at", ""), path.stem))


def find_candidate_file(root: Path, candidate_id: str) -> Path:
    root = root.resolve()
    ensure_antma_state(root)
    for path in iter_candidate_files(root):
        if path.stem == candidate_id:
            return path
    raise CandidateError(f"Candidate not found: {candidate_id}")


def show_candidate(root: Path, candidate_id: str) -> Dict[str, Any]:
    return load_candidate(find_candidate_file(root, candidate_id))


def delete_candidate(root: Path, candidate_id: str, actor: str = "antma-cli", reason: Optional[str] = None) -> None:
    root = root.resolve()
    path = find_candidate_file(root, candidate_id)
    data = load_candidate(path)
    status = data.get("status")
    if status not in DELETABLE_STATUSES:
        raise CandidateError(f"Cannot delete candidate with status {status}: {candidate_id}")
    path.unlink()
    append_audit_event(
        root,
        "candidate.delete",
        candidate_id=candidate_id,
        from_status=status,
        actor=actor,
        reason=reason,
    )


def apply_gate_result(root: Path, path: Path, result: GateResult) -> Dict[str, Any]:
    data = load_candidate(path)
    from_status = data["status"]
    data["status"] = result.status
    data["reason_code"] = result.reason_code
    data["next_action"] = result.next_action
    data["updated_at"] = utc_now()
    data["conflicts"] = result.conflicts
    metadata = data.setdefault("metadata", {})
    metadata["gate_messages"] = list(result.messages)

    validate_candidate(data, root=None)
    target = candidate_path(root, data["candidate_id"], result.status)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if path.resolve() != target.resolve() and path.exists():
        path.unlink()
    append_audit_event(
        root,
        "review.run",
        candidate_id=data["candidate_id"],
        from_status=from_status,
        to_status=result.status,
        reason_code=result.reason_code,
        next_action=result.next_action,
        actor="antma-cli",
    )
    return data


def validate_candidate(data: Dict[str, Any], root: Optional[Path] = None) -> None:
    candidate_id = data.get("candidate_id")
    if not isinstance(candidate_id, str) or not CANDIDATE_ID_RE.match(candidate_id):
        raise CandidateValidationError("candidate_id must match cand_YYYYMMDD_HHMMSS_<hex>.")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise CandidateValidationError("schema_version must be 0.2.")
    _require_non_empty(data, "summary")
    _require_non_empty(data, "text")
    CandidateStatus(data.get("status"))
    Scope(data.get("scope"))
    Risk(data.get("risk"))
    CandidateSensitivity(data.get("sensitivity"))

    source = _require_dict(data, "source")
    source_kind = SourceKind(source.get("kind")).value
    if source_kind == SourceKind.FILE.value:
        _require_non_empty(source, "path")
        source_hash = source.get("hash")
        if not isinstance(source_hash, str) or not source_hash.startswith("sha256:"):
            raise CandidateValidationError("source.hash must use sha256: prefix for file source.")
    else:
        if source.get("hash") is not None:
            raise CandidateValidationError("source.hash must be null for non-file sources.")
        _require_non_empty(source, "locator")
        _require_non_empty(source, "observed_at")

    destination = _require_dict(data, "destination")
    destination_path = _require_non_empty(destination, "path")
    if root is not None:
        try:
            resolve_destination(root, destination_path)
        except PathValidationError as error:
            raise CandidateValidationError(str(error)) from error

    evidence = data.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise CandidateValidationError("evidence must be a non-empty list.")
    for item in evidence:
        if not isinstance(item, dict):
            raise CandidateValidationError("evidence items must be objects.")
        _require_non_empty(item, "kind")
        _require_non_empty(item, "locator")

    if not isinstance(data.get("supersedes", []), list):
        raise CandidateValidationError("supersedes must be a list.")


def _require_dict(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise CandidateValidationError(f"{key} must be an object.")
    return value


def _require_non_empty(data: Dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CandidateValidationError(f"{key} must be non-empty.")
    return value
