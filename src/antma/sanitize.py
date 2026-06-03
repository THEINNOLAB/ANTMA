"""Privacy and secret scanning helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b[A-Z0-9_]*(?:API|ACCESS|SECRET|TOKEN|KEY)[A-Z0-9_]*\s*=\s*[^\s]{12,}"),
)

PRIVATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Us" + r"ers/[A-Za-z0-9._-]+/"),
    re.compile(r"\btele" + r"gram:\d+\b", re.IGNORECASE),
)

BINARY_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".antma",
    "dist",
    "build",
}
RUNTIME_ARTIFACT_DIRS = {".openclaw"}
ROOT_RUNTIME_ARTIFACT_FILES = {
    "HEARTBEAT.md",
    "IDENTITY.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    text: str


def scan_text(text: str, path: str = "<text>") -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, line_number, "secret-pattern", line.strip()))
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, line_number, "private-context", line.strip()))
    return findings


def scan_path(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if should_exclude(relative):
            continue
        runtime_dir = next((part for part in relative.parts if part in RUNTIME_ARTIFACT_DIRS), None)
        if runtime_dir:
            if relative.name == runtime_dir:
                findings.append(
                    Finding(
                        str(relative),
                        0,
                        "runtime-artifact",
                        "Agent runtime workspace artifacts must not be published.",
                    )
                )
            continue
        if (
            path.is_file()
            and len(relative.parts) == 1
            and relative.name in ROOT_RUNTIME_ARTIFACT_FILES
        ):
            findings.append(
                Finding(
                    str(relative),
                    0,
                    "runtime-artifact",
                    "Agent runtime root workspace file must not be published.",
                )
            )
            continue
        if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(text, str(relative)))
    return findings


def should_exclude(relative: Path) -> bool:
    return any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in relative.parts)


def format_findings(findings: list[Finding]) -> str:
    if not findings:
        return "No privacy findings."
    return "\n".join(
        f"{finding.path}:{finding.line}: {finding.rule}: {finding.text}"
        for finding in findings
    )
