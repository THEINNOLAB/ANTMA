"""Placeholder for a stateful-agent memory adapter."""

from antma.adapters.base import MemoryBackend
from antma.schema import MemoryRecord


class LettaBackend(MemoryBackend):
    name = "letta"

    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        raise NotImplementedError("Stateful-agent adapter is not implemented yet.")

