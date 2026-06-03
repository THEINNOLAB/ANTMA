"""Workspace scaffolding."""

from __future__ import annotations

from pathlib import Path


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


def create_workspace(root: Path, overwrite: bool = False) -> list[Path]:
    root = root.resolve()
    written: list[Path] = []
    for relative_path, content in TEMPLATES.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            continue
        target.write_text(content, encoding="utf-8")
        written.append(target)
    return written
