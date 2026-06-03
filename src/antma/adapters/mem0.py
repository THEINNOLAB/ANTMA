"""Placeholder for a Mem0 adapter.

This module intentionally does not import third-party packages. A future adapter
must be read-only by default and preserve provenance.
"""

from antma.adapters.base import MemoryBackend
from antma.schema import MemoryRecord


class Mem0Backend(MemoryBackend):
    name = "mem0"

    def search(self, query: str, limit: int = 10) -> list[MemoryRecord]:
        raise NotImplementedError("Mem0 adapter is not implemented yet.")

