"""Placeholder for a temporal graph adapter."""

from antma.adapters.base import MemoryBackend
from antma.schema import MemoryRecord


class GraphitiBackend(MemoryBackend):
    name = "graphiti"

    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        raise NotImplementedError("Graph adapter is not implemented yet.")

