from __future__ import annotations

# pylint: disable=unused-argument

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

import pytest

from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.report.report_tokens_scan import scan


def _calls() -> list[list[str]]:
    return []


@dataclass
class Runner:
    root: Path
    git_ok: bool = True
    calls: list[list[str]] = field(default_factory=_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        self.calls.append(list(argv))
        if list(argv)[:2] == ["git", "rev-parse"]:
            if not self.git_ok:
                return CommandResult(tuple(argv), 1, "", "not a git repo", 0.01)
            return CommandResult(tuple(argv), 0, str(self.root), "", 0.01)
        return CommandResult(tuple(argv), 1, "", "gh transient failure", 0.01)


def _write_run(base: Path, *, skill: str, good_tokens: bool = True) -> None:
    run = base / "larch-logs" / skill / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 1, "started_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"}), encoding="utf-8")
    token_name = "token-report-final.json" if skill == "design" else "token-report.json"
    report: dict[str, object] = {"claude": {"totals": {"total": 10}}, "BUCKETS_claude": {"input": 10}}
    if not good_tokens:
        report: dict[str, object] = {"claude": {"totals": {}}}
    _ = (run / token_name).write_text(json.dumps(report), encoding="utf-8")
    _ = (run / "run-params.json").write_text(json.dumps({}), encoding="utf-8")


def test_scan_per_skill_basename_and_workflow(tmp_path: Path) -> None:
    _write_run(tmp_path, skill="design")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].workflow == ""
    assert result.records[0].url == "https://github.com/o/r/issues/1"


def test_scan_warns_missing_slug_and_skips_incomplete(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_run(tmp_path, skill="implement", good_tokens=False)
    result = scan(Runner(tmp_path), skill="implement")
    assert result.repo_slug is None
    assert not result.records
    captured = capsys.readouterr()
    assert "could not resolve GitHub repo" in captured.err
    assert "lacks vendor totals" in captured.err


def test_scan_rejects_git_root_failure(tmp_path: Path) -> None:
    runner = Runner(tmp_path, git_ok=False)
    with pytest.raises(ShipError):
        _ = scan(runner, skill="implement", repo_override="o/r")


def test_scan_rejects_invalid_repo_override(tmp_path: Path) -> None:
    _write_run(tmp_path, skill="implement")
    with pytest.raises(ShipError):
        _ = scan(Runner(tmp_path), skill="implement", repo_override="../bad/repo")


def test_scan_blank_url_when_slug_unresolved(tmp_path: Path) -> None:
    _write_run(tmp_path, skill="implement")
    result = scan(Runner(tmp_path), skill="implement")
    assert result.records[0].url == ""


def test_scan_warns_empty_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "larch-logs" / "implement" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text("{}", encoding="utf-8")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert not result.records
    assert "lacks numeric issue_number" in capsys.readouterr().err


def test_scan_skips_symlinked_run_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_run(tmp_path / "outside", skill="implement")
    log_base = tmp_path / "larch-logs" / "implement"
    log_base.mkdir(parents=True, exist_ok=True)
    (log_base / "linked").symlink_to(tmp_path / "outside" / "larch-logs" / "implement" / "run1")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert not result.records
    assert "is a symlink; skipping" in capsys.readouterr().err


def test_scan_skips_symlinked_token_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "larch-logs" / "implement" / "run1"
    run.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    _ = outside.write_text(json.dumps({"BUCKETS_claude": {"input": 10}}), encoding="utf-8")
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 1}), encoding="utf-8")
    (run / "token-report.json").symlink_to(outside)
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert not result.records
    assert "token-report.json is a symlink; skipping" in capsys.readouterr().err


def test_scan_rejects_invalid_limit_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_run(tmp_path, skill="implement")
    monkeypatch.setenv("LARCH_REPORT_TOKENS_LIMIT", "100x")
    with pytest.raises(ShipError):
        _ = scan(Runner(tmp_path), skill="implement", repo_override="o/r")


def test_scan_warns_missing_skill_token_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "larch-logs" / "design" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 1}), encoding="utf-8")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert not result.records
    assert "has no token-report-final.json" in capsys.readouterr().err


def test_scan_warns_and_skips_invalid_auxiliary_json(tmp_path: Path) -> None:
    run = tmp_path / "larch-logs" / "design" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 1}), encoding="utf-8")
    _ = (run / "token-report-final.json").write_text(json.dumps({"claude": {"totals": {"total": 10}}, "BUCKETS_claude": {"input": 10}}), encoding="utf-8")
    _ = (run / "timing-report-final.json").write_text("{", encoding="utf-8")
    _ = (run / "run-params.json").write_text("{", encoding="utf-8")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1


def test_scan_warns_and_skips_non_object_manifest_and_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log_base = tmp_path / "larch-logs" / "implement"
    run1 = log_base / "run1"
    run1.mkdir(parents=True)
    _ = (run1 / "manifest.json").write_text("[]", encoding="utf-8")
    run2 = log_base / "run2"
    run2.mkdir()
    _ = (run2 / "manifest.json").write_text(json.dumps({"issue_number": 2}), encoding="utf-8")
    _ = (run2 / "token-report.json").write_text("null", encoding="utf-8")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert not result.records
    captured = capsys.readouterr()
    assert "manifest for" in captured.err
    assert "is not a JSON object; skipping" in captured.err
    assert "token-report.json is not a JSON object" in captured.err


def test_scan_ignores_unknown_positive_bucket_keys(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "larch-logs" / "implement" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 1}), encoding="utf-8")
    _ = (run / "token-report.json").write_text(json.dumps({"BUCKETS_codex": {"surprise": 5}}), encoding="utf-8")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert not result.records
    assert "lacks vendor totals/BUCKETS" in capsys.readouterr().err


def test_scan_design_workflow_is_always_empty(tmp_path: Path) -> None:
    _write_run(tmp_path, skill="design")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert result.records[0].workflow == ""


def test_scan_implement_workflow_is_empty(tmp_path: Path) -> None:
    _write_run(tmp_path, skill="implement")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert result.records[0].workflow == ""


def test_scan_implement_skips_malformed_workflow_artifacts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_run(tmp_path, skill="implement")
    run = tmp_path / "larch-logs" / "implement" / "run1"
    _ = (run / "timing-report.json").write_text("{", encoding="utf-8")
    (run / "run-params.json").unlink()
    (run / "run-params.json").symlink_to(tmp_path / "missing-run-params.json")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert result.records[0].workflow == ""
    err = capsys.readouterr().err
    assert "invalid timing-report.json" not in err
    assert "run-params.json" not in err


def test_scan_accepts_claude_sub_only_tokens(tmp_path: Path) -> None:
    # A run with only claude_sub tokens (no main-agent claude) must pass _has_numeric_tokens
    # and surface a valid record — verifies that claude_sub _totals are read and the scan
    # does not reject the run as incomplete.
    run = tmp_path / "larch-logs" / "implement" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(
        json.dumps({"issue_number": 2, "started_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"}),
        encoding="utf-8",
    )
    _ = (run / "token-report.json").write_text(
        json.dumps({
            "claude": {"totals": {"total": 0}},
            "claude_sub": {"totals": {"total": 50}},
            "BUCKETS_claude_sub": {"input": 30, "cache_read": 10, "cache_create": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 10},
        }),
        encoding="utf-8",
    )
    _ = (run / "run-params.json").write_text(json.dumps({}), encoding="utf-8")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].claude_sub.total == 50


def _write_ledger_run(base: Path, *, skill: str, with_marks: bool = True) -> None:
    # A run that committed its token ledger but never finalized token-report{,-final}.json (issue #5133).
    run = base / "larch-logs" / skill / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(
        json.dumps({"issue_number": 7, "started_at": "2026-06-15T00:00:00Z", "updated_at": "2026-06-15T01:00:00Z"}),
        encoding="utf-8",
    )
    rows: list[dict[str, object]] = []
    if with_marks:
        rows.append({"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"})
    rows.append({"type": "vendor", "vendor": "codex", "input": 100, "output": 20, "cache_read": 50, "total": 170, "ts": "2026-06-15T00:00:05Z"})
    _ = (run / "larch-tokens-abc.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_scan_falls_back_to_token_ledger_when_final_absent(tmp_path: Path) -> None:
    _write_ledger_run(tmp_path, skill="design")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].codex.total == 170
    assert result.records[0].number == 7


def test_scan_ledger_fallback_applies_to_implement(tmp_path: Path) -> None:
    _write_ledger_run(tmp_path, skill="implement")
    result = scan(Runner(tmp_path), skill="implement", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].codex.total == 170


def test_scan_ledger_fallback_skips_without_marks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_ledger_run(tmp_path, skill="design", with_marks=False)
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert not result.records
    assert "has no token-report-final.json" in capsys.readouterr().err


def test_scan_falls_back_to_ledger_when_canonical_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "larch-logs" / "design" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 8}), encoding="utf-8")
    _ = (run / "token-report-final.json").write_text("{}", encoding="utf-8")
    rows = [
        {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
        {"type": "vendor", "vendor": "codex", "input": 50, "output": 10, "total": 60, "ts": "2026-06-15T00:00:05Z"},
    ]
    _ = (run / "larch-tokens-abc.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].codex.total == 60
    assert "recovering token report from committed ledger" in capsys.readouterr().err


def test_scan_falls_back_to_ledger_when_canonical_lacks_numeric_tokens(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = tmp_path / "larch-logs" / "design" / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 9}), encoding="utf-8")
    _ = (run / "token-report-final.json").write_text(json.dumps({"claude": {"totals": {}}}), encoding="utf-8")
    rows = [
        {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
        {"type": "vendor", "vendor": "cursor", "input": 40, "output": 5, "total": 45, "ts": "2026-06-15T00:00:05Z"},
    ]
    _ = (run / "larch-tokens-only.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].cursor.total == 45
    assert "recovering token report from committed ledger" in capsys.readouterr().err


def test_scan_ledger_fallback_uses_session_scoped_ledger(tmp_path: Path) -> None:
    run = tmp_path / "larch-logs" / "design" / "run1"
    run.mkdir(parents=True)
    session_id = "scoped-session-42"
    slug = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    _ = (run / "session-id").write_text(session_id, encoding="utf-8")
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 10}), encoding="utf-8")
    scoped_rows = [
        {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
        {"type": "vendor", "vendor": "codex", "input": 10, "output": 1, "total": 11, "ts": "2026-06-15T00:00:05Z"},
    ]
    orphan_rows = [
        {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
        {"type": "vendor", "vendor": "codex", "input": 900, "output": 90, "total": 990, "ts": "2026-06-15T00:00:05Z"},
    ]
    _ = (run / f"larch-tokens-{slug}.jsonl").write_text(
        "\n".join(json.dumps(row) for row in scoped_rows) + "\n",
        encoding="utf-8",
    )
    _ = (run / "larch-tokens-orphan.jsonl").write_text(
        "\n".join(json.dumps(row) for row in orphan_rows) + "\n",
        encoding="utf-8",
    )
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].codex.total == 11


def test_scan_ledger_fallback_oserror_skips_run(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _write_ledger_run(tmp_path, skill="design")

    def _raise_oserror(_ledgers: list[Path]) -> dict[str, object]:
        raise OSError("permission denied")

    monkeypatch.setattr("larch.report.tokens.build_report_from_ledgers", _raise_oserror)
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert not result.records
    err = capsys.readouterr().err
    assert "could not read token ledger for" in err
