"""ANTMA filesystem policy loading and defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # pragma: no cover - exercised on Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.9/3.10
    import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_CONFIG_TOML = """version = "0.2"
backend = "filesystem"
default_policy = "default"
project_root = "."
"""


DEFAULT_POLICY_TOML = """version = 1
name = "default"

[paths]
project_root = "."
allowed_destinations = ["MEMORY.md", "MEMORY.shared.md", "memory/**/*.md", "docs/**/*.md"]
denied_destinations = [".git/**", ".env", "**/*secret*", "**/*token*"]
deny_antma_destinations = true
allow_external_source = false

[promotion]
auto_promote_scopes = ["personal", "project", "shared"]
manual_review_scopes = ["persona", "ssot", "security"]
require_source_hash = true
allow_overwrite = false
require_append_only = true
snapshot_required = true
lock_timeout_seconds = 10

[conflict]
strategy = "manual_review"
show_context_lines = 3

[risk_thresholds]
auto_max_risk = "medium"
manual_min_risk = "high"
reject_min_risk = "critical"

[sensitivity]
auto_allowed = ["public", "internal"]
manual_review = ["sensitive"]
reject = ["secret"]

[freshness]
stale_days = 30
critical_stale_days = 90
unknown_freshness = "manual_review"

[text]
max_chars_auto = 1200
max_chars_manual = 4000

[routing]
on_low_risk_allowed = "auto_passed"
on_high_risk = "manual_review"
on_scope_review = "manual_review"
on_sensitive = "manual_review"
on_secret = "rejected"
on_missing_source = "blocked"
on_source_hash_mismatch = "blocked"
on_stale_source = "manual_review"
on_destination_outside_root = "blocked"
on_append_only_violation = "blocked"
"""


RISK_LEVELS = ("low", "medium", "high", "critical")
REQUIRED_POLICY_TABLES = (
    "paths",
    "promotion",
    "conflict",
    "risk_thresholds",
    "sensitivity",
    "freshness",
    "text",
    "routing",
)


class PolicyValidationError(ValueError):
    """Raised when a policy file is missing required foundation fields."""


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise PolicyValidationError("Policy TOML must decode to a table.")
    return data


def load_policy(path: Path) -> dict[str, Any]:
    policy = load_toml(path)
    validate_policy(policy)
    return policy


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("version") != 1:
        raise PolicyValidationError("Policy version must be 1.")
    if not policy.get("name"):
        raise PolicyValidationError("Policy name is required.")

    for table in REQUIRED_POLICY_TABLES:
        if not isinstance(policy.get(table), dict):
            raise PolicyValidationError(f"Policy table [{table}] is required.")

    thresholds = policy["risk_thresholds"]
    for key in ("auto_max_risk", "manual_min_risk", "reject_min_risk"):
        value = thresholds.get(key)
        if value not in RISK_LEVELS:
            raise PolicyValidationError(f"risk_thresholds.{key} must be one of {RISK_LEVELS}.")

    lock_timeout = policy["promotion"].get("lock_timeout_seconds")
    if not isinstance(lock_timeout, int) or lock_timeout <= 0:
        raise PolicyValidationError("promotion.lock_timeout_seconds must be a positive integer.")


def default_policy() -> dict[str, Any]:
    policy = tomllib.loads(DEFAULT_POLICY_TOML)
    validate_policy(policy)
    return policy
