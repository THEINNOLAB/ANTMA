"""Append-only promotion executor."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from antma.candidates import (
    CandidateError,
    candidate_path,
    find_candidate_file,
    iter_candidate_files,
    load_candidate,
    utc_now,
    write_candidate_data,
)
from antma.fs import atomic_write_text, relative_path_for_policy, resolve_destination, sha256_file, sha256_text
from antma.gates import GateEngine
from antma.ids import new_promotion_id
from antma.ledger import append_audit_event, append_jsonl
from antma.models import CandidateStatus, ReasonCode, SourceKind
from antma.policy import load_project_policy
from antma.snapshots import create_snapshot


PROMOTABLE_STATUSES = (CandidateStatus.AUTO_PASSED.value, CandidateStatus.APPROVED.value)


class PromotionError(CandidateError):
    """Raised when promotion cannot proceed."""


def run_promotions(
    root: Path,
    candidate_id: Optional[str] = None,
    dry_run: bool = False,
    fail_fast: bool = False,
    policy_name: str = "default",
) -> Dict[str, Any]:
    root = root.resolve()
    policy = load_project_policy(root, policy_name)
    files = promotable_files(root, candidate_id=candidate_id)
    results: List[Dict[str, Any]] = []
    for path in files:
        data = load_candidate(path)
        try:
            result = promote_one(root, path, data, policy, dry_run=dry_run)
        except Exception as error:
            result = fail_candidate(root, path, data, str(error))
            if fail_fast:
                results.append(result)
                break
        results.append(result)
    return {
        "dry_run": dry_run,
        "processed": len(results),
        "succeeded": sum(1 for result in results if result["status"] == "promoted"),
        "failed": sum(1 for result in results if result["status"] in {"failed", "blocked"}),
        "results": results,
    }


def promotable_files(root: Path, candidate_id: Optional[str] = None) -> List[Path]:
    if candidate_id:
        path = find_candidate_file(root, candidate_id)
        data = load_candidate(path)
        if data["status"] not in PROMOTABLE_STATUSES:
            raise PromotionError(f"Candidate is not promotable: {candidate_id}")
        return [path]
    files: List[Path] = []
    for status in PROMOTABLE_STATUSES:
        files.extend(iter_candidate_files(root, status=status))
    return sorted(files, key=lambda path: (load_candidate(path).get("created_at", ""), path.stem))


def promote_one(
    root: Path,
    path: Path,
    candidate: Dict[str, Any],
    policy: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    destination = resolve_destination(root, candidate["destination"]["path"])
    destination_relative = relative_path_for_policy(root, destination)
    promotion_id = new_promotion_id()
    if dry_run:
        return {
            "candidate_id": candidate["candidate_id"],
            "promotion_id": promotion_id,
            "destination": destination_relative,
            "status": "dry_run",
            "reason_code": candidate.get("reason_code"),
        }

    lock_path = lock_file_for_destination(root, destination_relative)
    acquire_lock(
        lock_path,
        timeout_seconds=policy["promotion"].get("lock_timeout_seconds", 10),
        payload={
            "pid": os.getpid(),
            "created_at": utc_now(),
            "destination": destination_relative,
            "candidate_id": candidate["candidate_id"],
        },
    )
    try:
        validate_promotion_phase(root, candidate, policy)
        before_text = destination.read_text(encoding="utf-8") if destination.exists() else ""
        destination_hash_before = sha256_text(before_text)
        block = render_append_block(promotion_id, candidate, destination_relative)
        after_text = before_text + block
        if before_text and not after_text.startswith(before_text):
            raise PromotionError("Append-only validation failed.")
        destination_hash_after = sha256_text(after_text)
        create_snapshot(
            root,
            promotion_id,
            candidate["candidate_id"],
            destination_relative,
            before_text,
            after_text,
            destination_hash_before,
            destination_hash_after,
        )
        atomic_write_text(destination, after_text, tmp_dir=root / ".antma" / "tmp")
        promotion = {
            "promotion_id": promotion_id,
            "candidate_id": candidate["candidate_id"],
            "destination": destination_relative,
            "created_at": utc_now(),
            "destination_hash_before": destination_hash_before,
            "destination_hash_after": destination_hash_after,
            "reason_code": candidate.get("reason_code"),
        }
        append_jsonl(root / ".antma" / "ledger" / "promotions.jsonl", promotion)
        append_audit_event(
            root,
            "promotion.run",
            candidate_id=candidate["candidate_id"],
            promotion_id=promotion_id,
            from_status=candidate["status"],
            to_status=CandidateStatus.PROMOTED.value,
            reason_code=candidate.get("reason_code"),
            actor="antma-cli",
        )
        candidate["status"] = CandidateStatus.PROMOTED.value
        candidate["next_action"] = "no_action"
        candidate["updated_at"] = utc_now()
        candidate.setdefault("metadata", {})["promotion_id"] = promotion_id
        write_candidate_data(root, candidate, old_path=path, validate_root=False)
        return {
            "candidate_id": candidate["candidate_id"],
            "promotion_id": promotion_id,
            "destination": destination_relative,
            "status": "promoted",
            "reason_code": candidate.get("reason_code"),
            "destination_hash_before": destination_hash_before,
            "destination_hash_after": destination_hash_after,
        }
    finally:
        release_lock(lock_path)


def validate_promotion_phase(root: Path, candidate: Dict[str, Any], policy: Dict[str, Any]) -> None:
    if candidate["status"] == CandidateStatus.AUTO_PASSED.value:
        result = GateEngine(policy, root).evaluate(candidate)
        if result.status != CandidateStatus.AUTO_PASSED.value:
            raise PromotionError(f"Gate no longer passes: {result.reason_code}")
    source = candidate["source"]
    if source["kind"] == SourceKind.FILE.value:
        source_path = Path(source["path"])
        resolved_source = source_path if source_path.is_absolute() else root / source_path
        if not resolved_source.is_file():
            raise PromotionError("Source file is missing.")
        if source.get("hash") != sha256_file(resolved_source):
            raise PromotionError("Source hash changed since review.")
    elif not candidate.get("evidence"):
        raise PromotionError("Hashless source candidates require evidence.")


def fail_candidate(root: Path, path: Path, candidate: Dict[str, Any], reason: str) -> Dict[str, Any]:
    candidate["status"] = CandidateStatus.FAILED.value
    candidate["reason_code"] = ReasonCode.PROMOTION_WRITE_FAILED.value
    candidate["next_action"] = "retry"
    candidate["updated_at"] = utc_now()
    candidate.setdefault("metadata", {})["failure_reason"] = reason
    write_candidate_data(root, candidate, old_path=path, validate_root=False)
    append_audit_event(
        root,
        "promotion.failed",
        candidate_id=candidate["candidate_id"],
        to_status=CandidateStatus.FAILED.value,
        reason_code=ReasonCode.PROMOTION_WRITE_FAILED.value,
        reason=reason,
        actor="antma-cli",
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "promotion_id": None,
        "destination": candidate["destination"]["path"],
        "status": "failed",
        "reason_code": ReasonCode.PROMOTION_WRITE_FAILED.value,
        "failure_reason": reason,
    }


def render_append_block(promotion_id: str, candidate: Dict[str, Any], destination: str) -> str:
    source_locator = candidate["source"].get("locator") or candidate["source"].get("path") or "manual"
    return (
        "\n\n"
        f'<!-- antma:promotion id="{promotion_id}" candidate="{candidate["candidate_id"]}" started -->\n\n'
        f"- {utc_now()[:10]}: {candidate['text']}\n\n"
        f"Source: `{source_locator}`  \n"
        f"Reason: `{candidate.get('reason_code')}`\n\n"
        f'<!-- antma:promotion id="{promotion_id}" candidate="{candidate["candidate_id"]}" ended -->\n'
    )


def lock_file_for_destination(root: Path, destination_relative: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", destination_relative)
    return root / ".antma" / "locks" / f"{safe}.lock"


def acquire_lock(lock_path: Path, timeout_seconds: int, payload: Dict[str, Any]) -> None:
    deadline = time.time() + timeout_seconds
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            return
        except FileExistsError:
            if can_break_lock(lock_path, timeout_seconds):
                lock_path.unlink()
                continue
            if time.time() >= deadline:
                raise PromotionError(f"Timed out waiting for lock: {lock_path}")
            time.sleep(0.1)


def can_break_lock(lock_path: Path, timeout_seconds: int) -> bool:
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        created_at = payload.get("created_at")
        pid = payload.get("pid")
        created = time.mktime(time.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return False
    if time.time() - created <= timeout_seconds:
        return False
    if isinstance(pid, int) and process_exists(pid):
        return False
    return True


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
