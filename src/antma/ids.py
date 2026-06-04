"""Stable identifier helpers for ANTMA filesystem state."""

from __future__ import annotations

import secrets
from datetime import datetime


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def _hex_suffix(length: int = 4) -> str:
    return secrets.token_hex(max(1, length // 2))[:length]


def new_candidate_id() -> str:
    return f"cand_{_timestamp()}_{_hex_suffix()}"


def new_promotion_id() -> str:
    return f"prom_{_timestamp()}_{_hex_suffix()}"


def new_event_id() -> str:
    return f"evt_{_timestamp()}_{_hex_suffix(8)}"
