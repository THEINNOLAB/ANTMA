"""Promotion snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from antma.candidates import utc_now


def create_snapshot(
    root: Path,
    promotion_id: str,
    candidate_id: str,
    destination_relative: str,
    before_text: Optional[str],
    after_text: str,
    destination_hash_before: str,
    destination_hash_after: str,
) -> Dict[str, object]:
    snapshot_root = root / ".antma" / "snapshots" / promotion_id
    before_path = snapshot_root / "before" / destination_relative
    after_path = snapshot_root / "after" / destination_relative
    before_path.parent.mkdir(parents=True, exist_ok=True)
    after_path.parent.mkdir(parents=True, exist_ok=True)
    before_path.write_text(before_text or "", encoding="utf-8")
    after_path.write_text(after_text, encoding="utf-8")
    manifest = {
        "promotion_id": promotion_id,
        "candidate_id": candidate_id,
        "destination": destination_relative,
        "destination_hash_before": destination_hash_before,
        "destination_hash_after": destination_hash_after,
        "created_at": utc_now(),
    }
    (snapshot_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_snapshot_manifest(root: Path, promotion_id: str) -> Dict[str, object]:
    path = root / ".antma" / "snapshots" / promotion_id / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))
