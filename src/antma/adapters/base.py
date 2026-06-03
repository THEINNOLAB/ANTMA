"""Adapter contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from antma.schema import MemoryRecord


class MemoryBackend(ABC):
    """Read-only backend contract for derived memory views."""

    name: str

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        """Return records with provenance."""

    def write(self, record: MemoryRecord) -> None:
        raise NotImplementedError(
            "Adapters must not write to canonical memory directly. "
            "Create a promotion candidate instead."
        )

