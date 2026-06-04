"""Filesystem primitives for ANTMA local state."""

from __future__ import annotations

import hashlib
import fnmatch
import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Union


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


def is_within_root(root: Path, path: Path) -> bool:
    root_path = root.resolve()
    try:
        path.resolve(strict=False).relative_to(root_path)
    except ValueError:
        return False
    return True


def relative_path_for_policy(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def fnmatch_policy_path(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace(os.sep, "/")
    for pattern in patterns:
        normalized_pattern = pattern.replace(os.sep, "/")
        if fnmatch.fnmatchcase(normalized, normalized_pattern):
            return True
        if "/**/" in normalized_pattern:
            zero_depth_pattern = normalized_pattern.replace("/**/", "/")
            if fnmatch.fnmatchcase(normalized, zero_depth_pattern):
                return True
    return False


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
