"""Recall priority resolver."""

from __future__ import annotations

from collections.abc import Iterable

from antma.schema import MemoryKind, MemoryRecord, MemoryStatus, Sensitivity


KIND_PRIORITY: dict[MemoryKind, int] = {
    MemoryKind.SOURCE_OF_TRUTH: 100,
    MemoryKind.SHARED_MEMORY: 80,
    MemoryKind.AGENT_LOCAL: 70,
    MemoryKind.DAILY_RAW: 50,
    MemoryKind.KNOWLEDGE_BANK: 45,
    MemoryKind.PROMOTION_CANDIDATE: 35,
    MemoryKind.EVIDENCE_PACKET: 30,
    MemoryKind.EXTERNAL_BACKEND: 10,
}

STATUS_PRIORITY: dict[MemoryStatus, int] = {
    MemoryStatus.CURATED: 30,
    MemoryStatus.CANDIDATE: 10,
    MemoryStatus.RAW: 0,
    MemoryStatus.SUPERSEDED: -50,
    MemoryStatus.REJECTED: -100,
}

SENSITIVITY_PRIORITY: dict[Sensitivity, int] = {
    Sensitivity.PUBLIC: 5,
    Sensitivity.INTERNAL: 0,
    Sensitivity.CONFIDENTIAL: -10,
    Sensitivity.SECRET: -1000,
}


def resolve(
    records: Iterable[MemoryRecord],
    query: str = "",
    limit: int = 10,
) -> list[MemoryRecord]:
    """Return records in ANTMA recall priority order."""

    terms = [term.lower() for term in query.split() if term.strip()]

    def score(record: MemoryRecord) -> tuple[int, str]:
        text = record.as_search_text().lower()
        match_score = sum(20 for term in terms if term in text)
        priority = (
            KIND_PRIORITY.get(record.kind, 0)
            + STATUS_PRIORITY.get(record.status, 0)
            + SENSITIVITY_PRIORITY.get(record.sensitivity, 0)
            + match_score
        )
        return priority, record.created_at

    usable = [record for record in records if record.status is not MemoryStatus.REJECTED]
    return sorted(usable, key=score, reverse=True)[:limit]

