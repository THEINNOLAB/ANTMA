"""Core ANTMA schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class MemoryKind(str, Enum):
    DAILY_RAW = "daily_raw"
    SHARED_MEMORY = "shared_memory"
    AGENT_LOCAL = "agent_local"
    SOURCE_OF_TRUTH = "source_of_truth"
    KNOWLEDGE_BANK = "knowledge_bank"
    PROMOTION_CANDIDATE = "promotion_candidate"
    EVIDENCE_PACKET = "evidence_packet"
    EXTERNAL_BACKEND = "external_backend"


class MemoryStatus(str, Enum):
    RAW = "raw"
    CANDIDATE = "candidate"
    CURATED = "curated"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class MemoryRecord:
    """A single memory unit with provenance."""

    id: str
    kind: MemoryKind
    title: str
    body: str
    source: str
    status: MemoryStatus = MemoryStatus.RAW
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    created_at: str = field(default_factory=utc_now)
    tags: tuple[str, ...] = ()
    source_hash: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)

    def as_search_text(self) -> str:
        parts = [self.title, self.body, self.source, " ".join(self.tags)]
        return "\n".join(part for part in parts if part)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "title": self.title,
            "body": self.body,
            "source": self.source,
            "status": self.status.value,
            "sensitivity": self.sensitivity.value,
            "created_at": self.created_at,
            "tags": list(self.tags),
            "source_hash": self.source_hash,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_markdown(cls, path: Path, body: str, kind: MemoryKind) -> "MemoryRecord":
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name
        return cls(
            id=str(path),
            kind=kind,
            title=title,
            body=body,
            source=str(path),
        )


@dataclass(frozen=True)
class EvidenceItem:
    label: str
    result: str
    evidence: str


@dataclass(frozen=True)
class EvidencePacket:
    objective: str
    status: str
    criteria: tuple[str, ...]
    evidence: tuple[EvidenceItem, ...]
    remaining_risk: str = "None identified."
    next_action: str = "None."
    created_at: str = field(default_factory=utc_now)
