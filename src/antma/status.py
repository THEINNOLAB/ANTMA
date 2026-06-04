"""Project status helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from antma.candidates import QUEUE_DIR_BY_STATUS
from antma.ledger import read_jsonl


def project_status(root: Path) -> Dict[str, object]:
    root = root.resolve()
    queues: Dict[str, int] = {}
    for status, directory in QUEUE_DIR_BY_STATUS.items():
        queue_dir = root / ".antma" / "queue" / directory
        queues[status] = len(list(queue_dir.glob("*.json"))) if queue_dir.exists() else 0
    return {
        "root": str(root),
        "queues": queues,
        "audit_events": len(read_jsonl(root / ".antma" / "ledger" / "audit.jsonl")),
        "promotions": len(read_jsonl(root / ".antma" / "ledger" / "promotions.jsonl")),
    }
