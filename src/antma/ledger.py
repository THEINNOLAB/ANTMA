"""JSONL ledger helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from antma.ids import new_event_id


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def append_audit_event(root: Path, action: str, **fields: Any) -> Dict[str, Any]:
    event = {
        "event_id": new_event_id(),
        "created_at": utc_now(),
        "action": action,
    }
    event.update(fields)
    append_jsonl(root / ".antma" / "ledger" / "audit.jsonl", event)
    return event


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def filter_jsonl(path: Path, candidate_id: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    for record in read_jsonl(path):
        if candidate_id is None or record.get("candidate_id") == candidate_id:
            yield record
