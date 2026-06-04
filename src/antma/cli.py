"""Command line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from antma.approvals import (
    ApprovalError,
    approve_candidate,
    edit_candidate as edit_approval_candidate,
    hold_candidate,
    list_approvals,
    reject_candidate,
    show_approval,
)
from antma.candidates import (
    CandidateError,
    CandidateValidationError,
    create_candidate as create_json_candidate,
    delete_candidate as delete_json_candidate,
    discover_project_root,
    list_candidates,
    show_candidate,
)
from antma.evidence import render_evidence_packet
from antma.executor import PromotionError, run_promotions
from antma.indexer import IndexCompatibilityError, MemoryIndex, first_heading, infer_kind
from antma.ledger import filter_jsonl, read_jsonl
from antma.models import CandidateSensitivity, CandidateStatus, Risk, Scope, SourceKind
from antma.policy import PolicyValidationError, load_project_policy, policy_path
from antma.promotion import render_promotion_candidate
from antma.review import run_review
from antma.sanitize import format_findings, scan_path
from antma.scaffold import WORKSPACE_SCHEMA_VERSION, create_workspace
from antma.schema import EvidenceItem, EvidencePacket, MemoryKind, MemoryRecord
from antma.status import project_status


VALID_EVIDENCE_STATUSES = ("pass", "partial", "failed", "blocked")
WORKSPACE_FORMAT = "antma-workspace"
CANONICAL_LEDGER = "markdown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="antma")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a memory workspace")
    init_parser.add_argument("path", nargs="?", type=Path, default=Path("."))
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--overwrite", nargs="?", const="scaffold", action="append", default=[])

    sanitize_parser = subparsers.add_parser("sanitize", help="Scan for private data")
    sanitize_parser.add_argument("path", type=Path)

    index_parser = subparsers.add_parser("index", help="Index Markdown files")
    index_parser.add_argument("path", type=Path)
    index_parser.add_argument("--db", type=Path, default=Path(".antma/index.db"))

    doctor_parser = subparsers.add_parser("doctor", help="Check workspace and index compatibility")
    doctor_parser.add_argument("path", type=Path)
    doctor_parser.add_argument("--db", type=Path, required=True)

    search_parser = subparsers.add_parser("search", help="Search an ANTMA index")
    search_parser.add_argument("query")
    search_parser.add_argument("--db", type=Path, default=Path(".antma/index.db"))
    search_parser.add_argument("--limit", type=int, default=10)

    promote_parser = subparsers.add_parser("promote", help="Create a promotion candidate")
    promote_parser.add_argument("source", type=Path)
    promote_parser.add_argument("--reason", required=True)
    promote_parser.add_argument("--output", type=Path)
    promote_parser.add_argument("--overwrite", action="store_true")

    candidate_parser = subparsers.add_parser("candidate", help="Manage JSON promotion candidates")
    candidate_subparsers = candidate_parser.add_subparsers(dest="candidate_command", required=True)

    candidate_create = candidate_subparsers.add_parser("create", help="Create a JSON candidate")
    candidate_create.add_argument("--source")
    candidate_create.add_argument(
        "--source-type",
        choices=[item.value for item in SourceKind],
        default=SourceKind.FILE.value,
    )
    candidate_create.add_argument("--destination", required=True)
    candidate_create.add_argument("--summary", required=True)
    candidate_create.add_argument("--text", required=True)
    candidate_create.add_argument("--scope", choices=[item.value for item in Scope], required=True)
    candidate_create.add_argument("--risk", choices=[item.value for item in Risk], required=True)
    candidate_create.add_argument(
        "--sensitivity",
        choices=[item.value for item in CandidateSensitivity],
        required=True,
    )
    candidate_create.add_argument("--supersedes", action="append", default=[])
    candidate_create.add_argument("--evidence", action="append", default=[])

    candidate_list = candidate_subparsers.add_parser("list", help="List JSON candidates")
    candidate_list.add_argument("--status", choices=[item.value for item in CandidateStatus])

    candidate_show = candidate_subparsers.add_parser("show", help="Show a JSON candidate")
    candidate_show.add_argument("candidate_id")

    candidate_delete = candidate_subparsers.add_parser("delete", help="Delete an unpromoted candidate")
    candidate_delete.add_argument("candidate_id")
    candidate_delete.add_argument("--reason")

    review_parser = subparsers.add_parser("review", help="Run policy gates")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)
    review_run = review_subparsers.add_parser("run", help="Evaluate candidates against policy")
    review_run.add_argument("candidate_id", nargs="?")
    review_run.add_argument("--all", action="store_true", dest="run_all")
    review_run.add_argument("--policy", default="default")
    review_run.add_argument("--json", action="store_true", dest="json_output")

    policy_parser = subparsers.add_parser("policy", help="Inspect or validate policy")
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_validate = policy_subparsers.add_parser("validate", help="Validate an ANTMA policy")
    policy_validate.add_argument("--policy", default="default")
    policy_show = policy_subparsers.add_parser("show", help="Show an ANTMA policy")
    policy_show.add_argument("--policy", default="default")

    approvals_parser = subparsers.add_parser("approvals", help="Manage manual candidate approvals")
    approvals_subparsers = approvals_parser.add_subparsers(dest="approvals_command", required=True)
    approvals_list = approvals_subparsers.add_parser("list", help="List candidates awaiting approval")
    approvals_list.add_argument("--status", choices=[CandidateStatus.MANUAL_REVIEW.value, CandidateStatus.HELD.value])
    approvals_show = approvals_subparsers.add_parser("show", help="Show a candidate awaiting approval")
    approvals_show.add_argument("candidate_id")
    approvals_approve = approvals_subparsers.add_parser("approve", help="Approve a candidate")
    approvals_approve.add_argument("candidate_id")
    approvals_approve.add_argument("--reviewer", default="local-user")
    approvals_reject = approvals_subparsers.add_parser("reject", help="Reject a candidate")
    approvals_reject.add_argument("candidate_id")
    approvals_reject.add_argument("--reason", required=True)
    approvals_reject.add_argument("--reviewer", default="local-user")
    approvals_hold = approvals_subparsers.add_parser("hold", help="Place a candidate on hold")
    approvals_hold.add_argument("candidate_id")
    approvals_hold.add_argument("--reason", required=True)
    approvals_hold.add_argument("--reviewer", default="local-user")
    approvals_edit = approvals_subparsers.add_parser("edit", help="Edit a candidate awaiting approval")
    approvals_edit.add_argument("candidate_id")
    approvals_edit.add_argument("--text")
    approvals_edit.add_argument("--scope", choices=[item.value for item in Scope])
    approvals_edit.add_argument("--risk", choices=[item.value for item in Risk])
    approvals_edit.add_argument("--sensitivity", choices=[item.value for item in CandidateSensitivity])
    approvals_edit.add_argument("--destination")
    approvals_edit.add_argument("--supersedes", action="append")

    evidence_parser = subparsers.add_parser("evidence", help="Create an evidence packet")
    evidence_parser.add_argument("--objective", required=True)
    evidence_parser.add_argument("--status", choices=VALID_EVIDENCE_STATUSES, required=True)
    evidence_parser.add_argument("--criterion", action="append", dest="criteria", required=True)
    evidence_parser.add_argument("--evidence", action="append", dest="evidence_items", required=True)
    evidence_parser.add_argument("--remaining-risk", default="None identified.")
    evidence_parser.add_argument("--next-action", default="None.")
    evidence_parser.add_argument("--output", type=Path, required=True)
    evidence_parser.add_argument("--overwrite", action="store_true")

    status_parser = subparsers.add_parser("status", help="Show ANTMA local state status")
    status_parser.add_argument("--json", action="store_true", dest="json_output")

    ledger_parser = subparsers.add_parser("ledger", help="Show ANTMA ledgers")
    ledger_subparsers = ledger_parser.add_subparsers(dest="ledger_command", required=True)
    ledger_show = ledger_subparsers.add_parser("show", help="Show ledger records")
    ledger_show.add_argument("--type", choices=("audit", "promotions"), default="audit")
    ledger_show.add_argument("--candidate")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "promote" and argv[1] == "run":
        return handle_promote_run_args(argv[2:])
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        try:
            overwrite_targets = parse_init_overwrite_targets(tuple(args.overwrite))
        except ValueError as error:
            parser.error(str(error))
        written = create_workspace(
            args.path,
            overwrite="scaffold" in overwrite_targets,
            force=args.force,
            overwrite_targets=overwrite_targets,
        )
        print(f"Created {len(written)} files in {args.path}")
        return 0

    if args.command == "sanitize":
        findings = scan_path(args.path)
        print(format_findings(findings))
        return 1 if findings else 0

    if args.command == "index":
        index = MemoryIndex(args.db)
        count = index.index_markdown_tree(args.path)
        print(f"Indexed {count} markdown files into {args.db}")
        return 0

    if args.command == "doctor":
        return doctor_workspace(args.path, args.db)

    if args.command == "search":
        index = MemoryIndex(args.db)
        try:
            results = index.search(args.query, limit=args.limit)
        except (IndexCompatibilityError, sqlite3.Error) as error:
            print(str(error), file=sys.stderr)
            return 1
        for result in results:
            print(f"{result['path']} [{result['kind']}] {result['title']}")
            print(f"  {result['snippet']}")
        return 0

    if args.command == "promote":
        return create_promotion_candidate(
            source=args.source,
            reason=args.reason,
            output=args.output,
            overwrite=args.overwrite,
        )

    if args.command == "candidate":
        return handle_candidate_command(args)

    if args.command == "review":
        return handle_review_command(args)

    if args.command == "policy":
        return handle_policy_command(args)

    if args.command == "approvals":
        return handle_approvals_command(args)

    if args.command == "evidence":
        return create_evidence_packet(
            objective=args.objective,
            status=args.status,
            criteria=tuple(args.criteria),
            evidence_values=tuple(args.evidence_items),
            remaining_risk=args.remaining_risk,
            next_action=args.next_action,
            output=args.output,
            overwrite=args.overwrite,
        )

    if args.command == "status":
        return handle_status_command(args)

    if args.command == "ledger":
        return handle_ledger_command(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def handle_promote_run_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="antma promote run")
    parser.add_argument("candidate_id", nargs="?")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    root = discover_project_root(Path.cwd())
    try:
        result = run_promotions(
            root,
            candidate_id=args.candidate_id,
            dry_run=args.dry_run,
            fail_fast=args.fail_fast,
        )
    except (PromotionError, CandidateError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in result["results"]:
            print(
                "{candidate_id}\t{status}\t{promotion_id}\t{destination}".format(
                    candidate_id=item.get("candidate_id"),
                    status=item.get("status"),
                    promotion_id=item.get("promotion_id"),
                    destination=item.get("destination"),
                )
            )
    return 0


def handle_candidate_command(args: argparse.Namespace) -> int:
    root = discover_project_root(Path.cwd())
    try:
        if args.candidate_command == "create":
            candidate = create_json_candidate(
                root=root,
                source=args.source,
                source_type=args.source_type,
                destination=args.destination,
                summary=args.summary,
                text=args.text,
                scope=args.scope,
                risk=args.risk,
                sensitivity=args.sensitivity,
                supersedes=tuple(args.supersedes),
                evidence_values=tuple(args.evidence),
            )
            print(candidate.candidate_id)
            return 0

        if args.candidate_command == "list":
            candidates = list_candidates(root, status=args.status)
            for candidate in candidates:
                print(
                    f"{candidate['candidate_id']}\t{candidate['status']}\t{candidate['summary']}"
                )
            return 0

        if args.candidate_command == "show":
            candidate = show_candidate(root, args.candidate_id)
            print(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True))
            return 0

        if args.candidate_command == "delete":
            delete_json_candidate(root, args.candidate_id, reason=args.reason)
            print(f"Deleted {args.candidate_id}")
            return 0
    except (CandidateError, CandidateValidationError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Unknown candidate command: {args.candidate_command}", file=sys.stderr)
    return 2


def handle_review_command(args: argparse.Namespace) -> int:
    root = discover_project_root(Path.cwd())
    try:
        if args.review_command == "run":
            results = run_review(
                root,
                candidate_id=args.candidate_id,
                run_all=args.run_all,
                policy_name=args.policy,
            )
            if args.json_output:
                print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                for result in results:
                    print(
                        "{candidate_id}\t{from_status}->{to_status}\t{reason_code}\t{next_action}".format(
                            **result
                        )
                    )
            return 0
    except (CandidateError, CandidateValidationError, PolicyValidationError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Unknown review command: {args.review_command}", file=sys.stderr)
    return 2


def handle_policy_command(args: argparse.Namespace) -> int:
    root = discover_project_root(Path.cwd())
    try:
        if args.policy_command == "validate":
            load_project_policy(root, args.policy)
            print(f"Policy {args.policy}: valid")
            return 0
        if args.policy_command == "show":
            path = policy_path(root, args.policy)
            if not path.exists():
                raise PolicyValidationError(f"Policy not found: {args.policy}")
            load_project_policy(root, args.policy)
            print(path.read_text(encoding="utf-8"), end="")
            return 0
    except PolicyValidationError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Unknown policy command: {args.policy_command}", file=sys.stderr)
    return 2


def handle_approvals_command(args: argparse.Namespace) -> int:
    root = discover_project_root(Path.cwd())
    try:
        if args.approvals_command == "list":
            for candidate in list_approvals(root, status=args.status):
                print(
                    f"{candidate['candidate_id']}\t{candidate['status']}\t{candidate['summary']}"
                )
            return 0
        if args.approvals_command == "show":
            candidate = show_approval(root, args.candidate_id)
            print(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.approvals_command == "approve":
            candidate = approve_candidate(root, args.candidate_id, reviewer=args.reviewer)
            print(f"Approved {candidate['candidate_id']}")
            return 0
        if args.approvals_command == "reject":
            candidate = reject_candidate(
                root,
                args.candidate_id,
                reason=args.reason,
                reviewer=args.reviewer,
            )
            print(f"Rejected {candidate['candidate_id']}")
            return 0
        if args.approvals_command == "hold":
            candidate = hold_candidate(
                root,
                args.candidate_id,
                reason=args.reason,
                reviewer=args.reviewer,
            )
            print(f"Held {candidate['candidate_id']}")
            return 0
        if args.approvals_command == "edit":
            candidate = edit_approval_candidate(
                root,
                args.candidate_id,
                proposed_text=args.text,
                scope=args.scope,
                risk=args.risk,
                sensitivity=args.sensitivity,
                destination=args.destination,
                supersedes=args.supersedes,
            )
            print(f"Edited {candidate['candidate_id']}")
            return 0
    except (ApprovalError, CandidateError, CandidateValidationError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Unknown approvals command: {args.approvals_command}", file=sys.stderr)
    return 2


def handle_status_command(args: argparse.Namespace) -> int:
    root = discover_project_root(Path.cwd())
    status = project_status(root)
    if args.json_output:
        print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Root: {status['root']}")
        for name, count in status["queues"].items():
            print(f"{name}: {count}")
        print(f"audit_events: {status['audit_events']}")
        print(f"promotions: {status['promotions']}")
    return 0


def handle_ledger_command(args: argparse.Namespace) -> int:
    root = discover_project_root(Path.cwd())
    ledger_name = "promotions.jsonl" if args.type == "promotions" else "audit.jsonl"
    path = root / ".antma" / "ledger" / ledger_name
    records = (
        list(filter_jsonl(path, candidate_id=args.candidate))
        if args.candidate
        else read_jsonl(path)
    )
    for record in records:
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


def parse_init_overwrite_targets(values: tuple[str, ...]) -> set[str]:
    allowed = {"scaffold", "config", "policy"}
    targets: set[str] = set()
    for value in values:
        for part in value.split(","):
            target = part.strip()
            if not target:
                continue
            if target not in allowed:
                raise ValueError(
                    "init --overwrite must be one of: scaffold, config, policy"
                )
            targets.add(target)
    return targets


def doctor_workspace(path: Path, db_path: Path) -> int:
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        print(f"Workspace path must be an existing directory: {path}", file=sys.stderr)
        return 2

    issues = workspace_manifest_issues(root)
    index = MemoryIndex(db_path)
    try:
        index.validate()
    except (IndexCompatibilityError, sqlite3.Error) as error:
        issues.append(str(error))

    if issues:
        print("ANTMA doctor found issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("ANTMA doctor: healthy")
    return 0


def workspace_manifest_issues(root: Path) -> list[str]:
    manifest = root / "antma.json"
    if not manifest.exists():
        return ["Workspace manifest is missing. Run: antma init PATH"]
    if not manifest.is_file():
        return ["Workspace manifest path is not a file: antma.json"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"Workspace manifest is invalid JSON: {error.msg}"]
    if not isinstance(data, dict):
        return ["Workspace manifest must be a JSON object."]

    issues: list[str] = []
    if data.get("format") != WORKSPACE_FORMAT:
        issues.append(f"Workspace manifest format must be {WORKSPACE_FORMAT!r}.")
    if data.get("workspace_schema_version") != WORKSPACE_SCHEMA_VERSION:
        issues.append(
            f"Workspace schema version {data.get('workspace_schema_version')!r} is not supported."
        )
    if data.get("canonical_ledger") != CANONICAL_LEDGER:
        issues.append(f"Canonical ledger must be {CANONICAL_LEDGER!r}.")
    return issues


def create_promotion_candidate(
    source: Path,
    reason: str,
    output: Optional[Path],
    overwrite: bool = False,
) -> int:
    source = source.resolve()
    if not source.is_file():
        print(f"Source file not found: {source}", file=sys.stderr)
        return 1
    body = source.read_text(encoding="utf-8")
    workspace_root = discover_workspace_root(source.parent)
    relative_source = relative_to_or_self(source, workspace_root)
    target = output or workspace_root / "curation" / "promotions" / f"{source.stem}-promotion.md"
    record = MemoryRecord(
        id=str(relative_source),
        kind=MemoryKind(infer_kind(relative_source)),
        title=first_heading(body) or source.stem,
        body=body,
        source=str(relative_source),
        source_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )
    return write_output(target, render_promotion_candidate(record, reason), overwrite)


def create_evidence_packet(
    objective: str,
    status: str,
    criteria: tuple[str, ...],
    evidence_values: tuple[str, ...],
    remaining_risk: str,
    next_action: str,
    output: Path,
    overwrite: bool = False,
) -> int:
    try:
        evidence_items = tuple(parse_evidence_item(value) for value in evidence_values)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    packet = EvidencePacket(
        objective=objective,
        status=status,
        criteria=criteria,
        evidence=evidence_items,
        remaining_risk=remaining_risk,
        next_action=next_action,
    )
    return write_output(output, render_evidence_packet(packet), overwrite)


def parse_evidence_item(value: str) -> EvidenceItem:
    parts = [part.strip() for part in value.split("=", 2)]
    if len(parts) != 3 or not all(parts):
        raise ValueError("Evidence must use LABEL=RESULT=DETAIL with non-empty fields.")
    return EvidenceItem(label=parts[0], result=parts[1], evidence=parts[2])


def write_output(path: Path, content: str, overwrite: bool) -> int:
    target = path.resolve()
    if target.exists() and not overwrite:
        print(f"Refusing to overwrite existing file: {target}", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


def discover_workspace_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (
            (candidate / "antma.json").exists()
            or (candidate / "MEMORY.shared.md").exists()
            or (candidate / "ssot").exists()
            or (candidate / "daily").exists()
            or (candidate / "knowledge-bank").exists()
            or (candidate / "agents").exists()
        ):
            return candidate
    return current


def relative_to_or_self(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())
