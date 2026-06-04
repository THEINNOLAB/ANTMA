"""Command line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

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
from antma.indexer import IndexCompatibilityError, MemoryIndex, first_heading, infer_kind
from antma.models import CandidateSensitivity, CandidateStatus, Risk, Scope, SourceKind
from antma.promotion import render_promotion_candidate
from antma.sanitize import format_findings, scan_path
from antma.scaffold import WORKSPACE_SCHEMA_VERSION, create_workspace
from antma.schema import EvidenceItem, EvidencePacket, MemoryKind, MemoryRecord


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

    evidence_parser = subparsers.add_parser("evidence", help="Create an evidence packet")
    evidence_parser.add_argument("--objective", required=True)
    evidence_parser.add_argument("--status", choices=VALID_EVIDENCE_STATUSES, required=True)
    evidence_parser.add_argument("--criterion", action="append", dest="criteria", required=True)
    evidence_parser.add_argument("--evidence", action="append", dest="evidence_items", required=True)
    evidence_parser.add_argument("--remaining-risk", default="None identified.")
    evidence_parser.add_argument("--next-action", default="None.")
    evidence_parser.add_argument("--output", type=Path, required=True)
    evidence_parser.add_argument("--overwrite", action="store_true")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
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

    parser.error(f"Unknown command: {args.command}")
    return 2


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
