"""Workspace scaffolding."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

from antma.policy import DEFAULT_CONFIG_TOML, DEFAULT_POLICY_TOML


WORKSPACE_SCHEMA_VERSION = 1
WORKSPACE_MANIFEST = """{
  "format": "antma-workspace",
  "workspace_schema_version": 1,
  "canonical_ledger": "markdown"
}
"""


TEMPLATES: dict[str, str] = {
    "antma.json": WORKSPACE_MANIFEST,
    "MEMORY.shared.md": """# Shared Memory

Purpose: compact durable context shared by the team.

Keep this file short. Put current truth in `ssot/` and reusable knowledge in
`knowledge-bank/`.
""",
    "agents/default/MEMORY.md": """# Default Agent Memory

Purpose: role-scoped memory for one agent.

Store role boundaries, stable preferences, and long-lived operating notes here.
""",
    "ssot/example.md": """# Example Source Of Truth

Status: current

This is a generic example of reviewed current truth.
""",
    "daily/example.md": """# Daily Raw Log

Raw notes belong here. Promote only reviewed facts into durable memory.
""",
    "knowledge-bank/example.md": """# Knowledge Bank Example

Reusable knowledge belongs here: research, examples, methods, references.
""",
    "curation/promotions/example.md": """# Promotion Candidate Example

Status: candidate

Use this space to review whether raw memory should become durable memory.
""",
    "evidence/example-packet.md": """# Evidence Packet Example

Status: partial

## Objective

Describe the work.

## Evidence

- command or artifact path
- test result
- review result

## Remaining Risk

Describe unresolved risk.
""",
}


ANTMA_DIRECTORIES = (
    ".antma/policies",
    ".antma/queue/candidates",
    ".antma/queue/auto-passed",
    ".antma/queue/manual-review",
    ".antma/queue/approved",
    ".antma/queue/held",
    ".antma/queue/blocked",
    ".antma/queue/rejected",
    ".antma/queue/promoted",
    ".antma/queue/rolled-back",
    ".antma/queue/failed",
    ".antma/ledger",
    ".antma/snapshots",
    ".antma/locks",
    ".antma/tmp",
)

ANTMA_DEFAULT_FILES = {
    ".antma/config.toml": DEFAULT_CONFIG_TOML,
    ".antma/policies/default.toml": DEFAULT_POLICY_TOML,
}

ANTMA_LEDGER_FILES = (
    ".antma/ledger/audit.jsonl",
    ".antma/ledger/promotions.jsonl",
)


def create_workspace(
    root: Path,
    overwrite: bool = False,
    force: bool = False,
    overwrite_targets: Optional[Set[str]] = None,
) -> list[Path]:
    root = root.resolve()
    overwrite_targets = overwrite_targets or set()
    written: list[Path] = []
    for relative_path, content in TEMPLATES.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            continue
        target.write_text(content, encoding="utf-8")
        written.append(target)
    written.extend(
        create_antma_state(
            root,
            force=force,
            overwrite_config="config" in overwrite_targets,
            overwrite_policy="policy" in overwrite_targets,
        )
    )
    return written


def create_antma_state(
    root: Path,
    force: bool = False,
    overwrite_config: bool = False,
    overwrite_policy: bool = False,
) -> list[Path]:
    root = root.resolve()
    antma_root = root / ".antma"
    antma_exists = antma_root.exists()
    write_missing = force or not antma_exists
    written: list[Path] = []

    if write_missing:
        for relative_path in ANTMA_DIRECTORIES:
            target = root / relative_path
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
                written.append(target)

        for relative_path in ANTMA_LEDGER_FILES:
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("", encoding="utf-8")
                written.append(target)

    for relative_path, content in ANTMA_DEFAULT_FILES.items():
        target = root / relative_path
        should_overwrite = (
            (relative_path == ".antma/config.toml" and overwrite_config)
            or (relative_path == ".antma/policies/default.toml" and overwrite_policy)
        )
        if should_overwrite or (write_missing and not target.exists()):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(target)

    return written
