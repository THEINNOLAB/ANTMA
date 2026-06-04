from pathlib import Path

import pytest

from antma.cli import main
from antma.fs import PathValidationError, resolve_destination
from antma.policy import PolicyValidationError, load_policy, validate_policy


ANTMA_LAYOUT_PATHS = (
    ".antma/config.toml",
    ".antma/policies/default.toml",
    ".antma/queue/candidates",
    ".antma/queue/auto-passed",
    ".antma/queue/manual-review",
    ".antma/queue/approved",
    ".antma/queue/held",
    ".antma/queue/blocked",
    ".antma/queue/rejected",
    ".antma/queue/promoted",
    ".antma/queue/rolled-back",
    ".antma/queue/failed",
    ".antma/ledger/audit.jsonl",
    ".antma/ledger/promotions.jsonl",
    ".antma/snapshots",
    ".antma/locks",
    ".antma/tmp",
)


def test_init_creates_antma_layout(tmp_path: Path):
    root = tmp_path / "team-memory"

    assert main(["init", str(root)]) == 0

    for relative_path in ANTMA_LAYOUT_PATHS:
        assert (root / relative_path).exists(), relative_path


def test_init_path_defaults_to_current_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)

    assert main(["init"]) == 0

    assert (tmp_path / "antma.json").exists()
    assert (tmp_path / ".antma" / "config.toml").exists()


def test_init_force_supplements_missing_antma_state_without_overwriting(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0

    config = root / ".antma" / "config.toml"
    ledger = root / ".antma" / "ledger" / "audit.jsonl"
    missing_queue = root / ".antma" / "queue" / "held"
    config.write_text('version = "custom"\n', encoding="utf-8")
    ledger.write_text('{"custom": true}\n', encoding="utf-8")
    missing_queue.rmdir()

    assert main(["init", str(root), "--force"]) == 0

    assert missing_queue.exists()
    assert config.read_text(encoding="utf-8") == 'version = "custom"\n'
    assert ledger.read_text(encoding="utf-8") == '{"custom": true}\n'


def test_init_targeted_overwrite_config_and_policy(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0

    config = root / ".antma" / "config.toml"
    policy = root / ".antma" / "policies" / "default.toml"
    config.write_text('version = "custom"\n', encoding="utf-8")
    policy.write_text('version = 999\nname = "bad"\n', encoding="utf-8")

    assert main(["init", str(root), "--overwrite", "config", "--overwrite", "policy"]) == 0

    assert 'version = "0.2"' in config.read_text(encoding="utf-8")
    assert "lock_timeout_seconds = 10" in policy.read_text(encoding="utf-8")


def test_policy_loads_default_toml(tmp_path: Path):
    root = tmp_path / "team-memory"
    assert main(["init", str(root)]) == 0

    policy = load_policy(root / ".antma" / "policies" / "default.toml")

    assert policy["name"] == "default"
    assert policy["promotion"]["lock_timeout_seconds"] == 10


def test_policy_validation_rejects_bad_threshold():
    policy = {
        "version": 1,
        "name": "bad",
        "paths": {},
        "promotion": {"lock_timeout_seconds": 10},
        "conflict": {},
        "risk_thresholds": {
            "auto_max_risk": "unknown",
            "manual_min_risk": "high",
            "reject_min_risk": "critical",
        },
        "sensitivity": {},
        "freshness": {},
        "text": {},
        "routing": {},
    }

    with pytest.raises(PolicyValidationError):
        validate_policy(policy)


def test_resolve_destination_rejects_root_escape_and_antma_destination(tmp_path: Path):
    root = tmp_path / "team-memory"
    root.mkdir()

    assert resolve_destination(root, "memory/project.md") == root.resolve() / "memory" / "project.md"

    with pytest.raises(PathValidationError):
        resolve_destination(root, "../outside.md")
    with pytest.raises(PathValidationError):
        resolve_destination(root, ".antma/config.toml")
