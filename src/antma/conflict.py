"""Conservative conflict detection for candidate review."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List


WORD_RE = re.compile(r"[A-Za-z0-9가-힣_]+")
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "operating",
    "reply",
    "replies",
}


def detect_conflicts(destination: Path, text: str, context_lines: int = 3) -> List[Dict[str, object]]:
    if not destination.exists() or not destination.is_file():
        return []

    destination_text = destination.read_text(encoding="utf-8")
    if normalize(text) in normalize(destination_text):
        return []

    candidate_tokens = meaningful_tokens(text)
    if len(candidate_tokens) < 2:
        return []

    lines = destination_text.splitlines()
    conflicts: List[Dict[str, object]] = []
    for index, line in enumerate(lines):
        line_tokens = meaningful_tokens(line)
        overlap = sorted(candidate_tokens.intersection(line_tokens))
        if len(overlap) < 2:
            continue
        start = max(0, index - context_lines)
        end = min(len(lines), index + context_lines + 1)
        conflicts.append(
            {
                "kind": "text_overlap",
                "line": index + 1,
                "overlap": overlap,
                "excerpt": "\n".join(lines[start:end]),
            }
        )
        break
    return conflicts


def meaningful_tokens(text: str) -> set[str]:
    tokens = {token.lower() for token in WORD_RE.findall(text)}
    return {token for token in tokens if len(token) > 2 and token not in STOP_WORDS}


def normalize(text: str) -> str:
    return " ".join(text.lower().split())
