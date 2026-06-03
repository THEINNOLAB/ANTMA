from pathlib import Path

from antma.sanitize import scan_path, scan_text


def test_scan_text_detects_private_path():
    findings = scan_text("log stored at " + "/Us" + "ers/example/private/file.md")

    assert findings
    assert findings[0].rule == "private-context"


def test_scan_text_detects_secret_assignment():
    findings = scan_text("SERVICE_" + "API_" + "KEY=" + "abc123456789")

    assert findings
    assert findings[0].rule == "secret-pattern"


def test_scan_path_accepts_clean_text(tmp_path: Path):
    (tmp_path / "note.md").write_text("Generic public example.", encoding="utf-8")

    assert scan_path(tmp_path) == []


def test_scan_path_detects_agent_runtime_artifacts(tmp_path: Path):
    (tmp_path / ".openclaw").mkdir()
    (tmp_path / ".openclaw" / "workspace-state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "HEARTBEAT.md").write_text("local runtime note", encoding="utf-8")

    findings = scan_path(tmp_path)

    assert {finding.rule for finding in findings} == {"runtime-artifact"}
    assert {finding.path for finding in findings} == {
        ".openclaw",
        "HEARTBEAT.md",
    }


def test_scan_path_ignores_cache_directories(tmp_path: Path):
    cache = tmp_path / ".pytest_cache"
    cache.mkdir()
    (cache / "note.txt").write_text("SERVICE_" + "API_" + "KEY=" + "abc123456789", encoding="utf-8")

    assert scan_path(tmp_path) == []
