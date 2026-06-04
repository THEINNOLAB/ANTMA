"""Policy gate engine for ANTMA 0.2 candidates."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from antma.candidates import CandidateValidationError, validate_candidate
from antma.conflict import detect_conflicts
from antma.fs import (
    PathValidationError,
    fnmatch_policy_path,
    is_within_root,
    relative_path_for_policy,
    resolve_destination,
    sha256_file,
)
from antma.models import CandidateStatus, GateResult, ReasonCode, SourceKind


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class GateEngine:
    def __init__(self, policy: Dict[str, Any], root: Path):
        self.policy = policy
        self.root = root.resolve()

    def evaluate(self, candidate: Dict[str, Any]) -> GateResult:
        try:
            validate_candidate(candidate, root=None)
        except CandidateValidationError as error:
            return self._blocked(ReasonCode.POLICY_INVALID.value, "update_policy", str(error))

        destination_result = self._validate_destination(candidate)
        if destination_result is not None:
            return destination_result

        source_result = self._validate_source(candidate)
        if source_result is not None:
            return source_result

        sensitivity = candidate["sensitivity"]
        if sensitivity == "secret":
            return GateResult(
                status=CandidateStatus.REJECTED.value,
                reason_code=ReasonCode.CLASSIFIED_DATA_DETECTED.value,
                next_action="no_action",
                messages=["Secret sensitivity candidates are rejected by policy."],
            )
        if sensitivity in self.policy["sensitivity"].get("manual_review", ()):
            return GateResult(
                status=CandidateStatus.MANUAL_REVIEW.value,
                reason_code=ReasonCode.SENSITIVE_DATA_DETECTED.value,
                next_action="manual_review",
                messages=["Sensitive candidates require manual review."],
            )

        stale_result = self._validate_freshness(candidate)
        if stale_result is not None:
            return stale_result

        scope = candidate["scope"]
        if scope in self.policy["promotion"].get("manual_review_scopes", ()):
            return GateResult(
                status=CandidateStatus.MANUAL_REVIEW.value,
                reason_code=ReasonCode.SCOPE_REQUIRES_REVIEW.value,
                next_action="manual_review",
                messages=[f"Scope requires manual review: {scope}"],
            )

        risk_result = self._validate_risk(candidate["risk"])
        if risk_result is not None:
            return risk_result

        text_result = self._validate_text(candidate["text"])
        if text_result is not None:
            return text_result

        conflict_result = self._validate_conflicts(candidate)
        if conflict_result is not None:
            return conflict_result

        if candidate["destination"].get("mode") != "append":
            return self._blocked(
                ReasonCode.APPEND_ONLY_REQUIRED.value,
                "edit_candidate",
                "Only append mode is allowed by the default policy.",
            )

        return GateResult(
            status=CandidateStatus.AUTO_PASSED.value,
            reason_code=ReasonCode.LOW_RISK_AUTO_ALLOWED.value,
            next_action="promote",
            messages=["Candidate passed the default policy gate."],
        )

    def _validate_destination(self, candidate: Dict[str, Any]) -> Optional[GateResult]:
        destination = candidate["destination"]["path"]
        try:
            resolved = resolve_destination(self.root, destination)
        except PathValidationError as error:
            return self._blocked(
                ReasonCode.DESTINATION_OUTSIDE_ROOT.value,
                "choose_destination",
                str(error),
            )

        relative = relative_path_for_policy(self.root, resolved)
        paths_policy = self.policy["paths"]
        if paths_policy.get("deny_antma_destinations", True) and ".antma" in Path(relative).parts:
            return self._blocked(
                ReasonCode.INVALID_DESTINATION.value,
                "choose_destination",
                f"Destination cannot be inside .antma: {destination}",
            )
        if fnmatch_policy_path(relative, paths_policy.get("denied_destinations", ())):
            return self._blocked(
                ReasonCode.INVALID_DESTINATION.value,
                "choose_destination",
                f"Destination is denied by policy: {relative}",
            )
        allowed = paths_policy.get("allowed_destinations", ())
        if allowed and not fnmatch_policy_path(relative, allowed):
            return self._blocked(
                ReasonCode.INVALID_DESTINATION.value,
                "choose_destination",
                f"Destination is not allowed by policy: {relative}",
            )
        return None

    def _validate_source(self, candidate: Dict[str, Any]) -> Optional[GateResult]:
        source = candidate["source"]
        source_kind = source["kind"]
        require_source_hash = self.policy["promotion"].get("require_source_hash", True)
        if source_kind != SourceKind.FILE.value:
            if require_source_hash:
                return GateResult(
                    status=CandidateStatus.MANUAL_REVIEW.value,
                    reason_code=ReasonCode.SOURCE_HASH_MISSING.value,
                    next_action="manual_review",
                    messages=["Hashless source kinds require manual review."],
                )
            return None

        source_path_value = source["path"]
        source_path = Path(source_path_value)
        resolved_source = source_path if source_path.is_absolute() else self.root / source_path
        if not is_within_root(self.root, resolved_source) and not self.policy["paths"].get(
            "allow_external_source", False
        ):
            return self._blocked(
                ReasonCode.SOURCE_OUTSIDE_ROOT.value,
                "fix_source",
                f"Source escapes project root: {source_path_value}",
            )
        if not resolved_source.exists() or not resolved_source.is_file():
            return self._blocked(
                ReasonCode.SOURCE_MISSING.value,
                "fix_source",
                f"Source file is missing: {source_path_value}",
            )
        expected_hash = source.get("hash")
        actual_hash = sha256_file(resolved_source)
        if require_source_hash and not expected_hash:
            return GateResult(
                status=CandidateStatus.MANUAL_REVIEW.value,
                reason_code=ReasonCode.SOURCE_HASH_MISSING.value,
                next_action="manual_review",
                messages=["File source hash is missing."],
            )
        if expected_hash and expected_hash != actual_hash:
            return self._blocked(
                ReasonCode.SOURCE_HASH_MISMATCH.value,
                "refresh_source_hash",
                "Source hash changed since candidate creation.",
            )
        return None

    def _validate_freshness(self, candidate: Dict[str, Any]) -> Optional[GateResult]:
        source = candidate["source"]
        if source["kind"] != SourceKind.FILE.value:
            return None
        source_path = Path(source["path"])
        resolved_source = source_path if source_path.is_absolute() else self.root / source_path
        timestamp = parse_datetime(source.get("created_at"))
        if timestamp is None:
            try:
                timestamp = datetime.fromtimestamp(resolved_source.stat().st_mtime, timezone.utc)
            except OSError:
                return GateResult(
                    status=CandidateStatus.MANUAL_REVIEW.value,
                    reason_code=ReasonCode.SOURCE_FRESHNESS_UNKNOWN.value,
                    next_action="manual_review",
                    messages=["Source freshness could not be determined."],
                )
        age_days = (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).days
        stale_days = self.policy["freshness"].get("stale_days", 30)
        if age_days > stale_days:
            return GateResult(
                status=CandidateStatus.MANUAL_REVIEW.value,
                reason_code=ReasonCode.SOURCE_STALE.value,
                next_action="manual_review",
                messages=[f"Source is stale: {age_days} days old."],
            )
        return None

    def _validate_risk(self, risk: str) -> Optional[GateResult]:
        thresholds = self.policy["risk_thresholds"]
        if risk_at_least(risk, thresholds.get("reject_min_risk", "critical")):
            return GateResult(
                status=CandidateStatus.REJECTED.value,
                reason_code=ReasonCode.HIGH_RISK_REQUIRES_REVIEW.value,
                next_action="no_action",
                messages=[f"Risk is rejected by policy: {risk}"],
            )
        if risk_at_least(risk, thresholds.get("manual_min_risk", "high")):
            return GateResult(
                status=CandidateStatus.MANUAL_REVIEW.value,
                reason_code=ReasonCode.HIGH_RISK_REQUIRES_REVIEW.value,
                next_action="manual_review",
                messages=[f"Risk requires manual review: {risk}"],
            )
        return None

    def _validate_text(self, text: str) -> Optional[GateResult]:
        text_policy = self.policy["text"]
        max_manual = text_policy.get("max_chars_manual", 4000)
        max_auto = text_policy.get("max_chars_auto", 1200)
        if len(text) > max_manual:
            return self._blocked(
                ReasonCode.TEXT_TOO_LONG.value,
                "edit_candidate",
                "Candidate text is too long for manual review.",
            )
        if len(text) > max_auto:
            return GateResult(
                status=CandidateStatus.MANUAL_REVIEW.value,
                reason_code=ReasonCode.TEXT_TOO_LONG.value,
                next_action="manual_review",
                messages=["Candidate text exceeds auto-promotion length."],
            )
        return None

    def _validate_conflicts(self, candidate: Dict[str, Any]) -> Optional[GateResult]:
        strategy = self.policy["conflict"].get("strategy", "manual_review")
        if strategy != "manual_review":
            return None
        destination = resolve_destination(self.root, candidate["destination"]["path"])
        conflicts = detect_conflicts(
            destination,
            candidate["text"],
            context_lines=self.policy["conflict"].get("show_context_lines", 3),
        )
        if not conflicts:
            return None
        return GateResult(
            status=CandidateStatus.MANUAL_REVIEW.value,
            reason_code=ReasonCode.CONFLICT_DETECTED.value,
            next_action="resolve_conflict",
            messages=["Potential conflict detected in destination."],
            conflicts=conflicts,
        )

    def _blocked(self, reason_code: str, next_action: str, message: str) -> GateResult:
        return GateResult(
            status=CandidateStatus.BLOCKED.value,
            reason_code=reason_code,
            next_action=next_action,
            messages=[message],
        )


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def risk_at_least(value: str, threshold: str) -> bool:
    return RISK_ORDER[value] >= RISK_ORDER[threshold]
