"""Filesystem primitives for ANTMA local state."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional, Union


class PathValidationError(ValueError):
    """Raised when a path is unsafe for ANTMA filesystem operations."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def resolve_destination(root: Path, destination: Union[str, Path]) -> Path:
    """Resolve a destination inside root and reject root escape or .antma writes."""

    root_path = root.resolve()
    raw_destination = Path(destination)
    candidate = raw_destination if raw_destination.is_absolute() else root_path / raw_destination
    resolved = candidate.resolve(strict=False)

    try:
        relative = resolved.relative_to(root_path)
    except ValueError as error:
        raise PathValidationError(f"Destination escapes project root: {destination}") from error

    if ".antma" in relative.parts:
        raise PathValidationError(f"Destination cannot be inside .antma: {destination}")
    if not relative.parts:
        raise PathValidationError("Destination must be a file path inside the project root.")

    return resolved


def atomic_write_text(path: Path, content: str, tmp_dir: Optional[Path] = None) -> None:
    """Write text through a temp file and atomic replace on the same filesystem."""

    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = tmp_dir or target.parent
    staging_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=staging_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
