"""Promotion candidate helpers."""

from __future__ import annotations

from antma.schema import MemoryRecord, utc_now


def render_promotion_candidate(record: MemoryRecord, reason: str) -> str:
    tags = ", ".join(record.tags) if record.tags else "none"
    return f"""# Promotion Candidate: {record.title}

Created: {utc_now()}
Source: {record.source}
Source hash: {record.source_hash or "not provided"}
Current kind: {record.kind.value}
Current status: {record.status.value}
Sensitivity: {record.sensitivity.value}
Tags: {tags}

## Reason

{reason}

## Candidate Content

{record.body}

## Review

- [ ] accept as durable memory
- [ ] convert into source-of-truth update
- [ ] reject
- [ ] needs more evidence
"""

