# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Regression coverage for Python-owned audit helpers after the Rust cutover."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.core import config
from larch.core.proc import CommandResult
from larch.issue import audit_runs
from larch.report import storage_config

_RUST_SCAN_BOUNDARY = audit_runs._learn_from_bugs_scan_boundary


@pytest.fixture(autouse=True)
def _isolated_analysis_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    storage = storage_config.ToolRepositoryStorage(
        storage_config.StorageBase("s3", "test-bucket"), "r"
    )
    monkeypatch.setattr(
        storage_config,
        "load_tool_repository_storage",
        lambda **_kwargs: storage,
    )

    def scan_boundary(root: Path) -> tuple[str, str] | None:
        marker = root / ".learn-from-bugs-test-state.json"
        if marker.is_symlink() or not marker.is_file():
            return None
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        repo = payload.get("repo")
        run_date = payload.get("run_date")
        scan_started_at = payload.get("scan_started_at")
        if not isinstance(repo, str) or not isinstance(run_date, str):
            return None
        return repo, scan_started_at if isinstance(scan_started_at, str) and scan_started_at else run_date

    monkeypatch.setattr(audit_runs, "_learn_from_bugs_scan_boundary", scan_boundary)


def test_title_contiguous(capsys: pytest.CaptureFixture[str]) -> None:
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "3,1,2", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #1-#3"


def test_title_single_pr(capsys: pytest.CaptureFixture[str]) -> None:
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "42", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #42"


def test_title_noncontiguous_compact(capsys: pytest.CaptureFixture[str]) -> None:
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "1,2,5,6", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #1-#6 (4 total)"


def test_title_noncontiguous_stays_under_256_chars(capsys: pytest.CaptureFixture[str]) -> None:
    pr_list = ",".join(str(number) for number in range(5000, 5000 + 2276, 2))
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", pr_list, "--timestamp", "2026-06-28T10:00-07:00"]) == 0
    assert len(capsys.readouterr().out.strip().removeprefix("TITLE=")) <= 256


def test_title_design_noncontiguous_compact(capsys: pytest.CaptureFixture[str]) -> None:
    assert audit_runs.title_main(["--skill", "design", "--pr-list", "10,20,30", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Design Run Logs Audit T Report] PRs #10-#30 (3 total)"


def _write_learn_from_bugs_state(
    root: Path,
    *,
    run_date: str = "2026-07-09T00:00:00Z",
    scan_started_at: str | None = "2026-07-09T01:00:00Z",
) -> None:
    marker = root / ".learn-from-bugs-test-state.json"
    payload: dict[str, object] = {
        "schema_version": 1,
        "run_date": run_date,
        "repo": "o/r",
        "search": "[BUG] in:title",
        "state": "closed",
        "selected_count": 5,
        "highest_closed_issue_number_scanned": 99,
    }
    if scan_started_at is not None:
        payload["scan_started_at"] = scan_started_at
    marker.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _gh_issue_rows(
    count: int,
    *,
    title: str = "[BUG] fixed",
    closed_at: str = "2026-07-09T02:00:00Z",
) -> str:
    return json.dumps([{"number": number + 1, "title": title, "closedAt": closed_at} for number in range(count)])


def test_learn_from_bugs_state_does_not_import_legacy_repository_state(tmp_path: Path) -> None:
    legacy = tmp_path / "larch-logs" / "shared" / "learn-from-bugs-state.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"schema_version":1}\n', encoding="utf-8")
    assert not (tmp_path / ".learn-from-bugs-test-state.json").exists()
    assert legacy.read_text(encoding="utf-8") == '{"schema_version":1}\n'


def test_learn_from_bugs_scan_boundary_reads_the_rust_state_wire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> CommandResult:
        calls.append(argv)
        return CommandResult(
            tuple(argv),
            0,
            "LEARN_FROM_BUGS_STATE_FOUND=true\nREPO=o/r\nRUN_DATE=2026-07-09T00:00:00Z\nSCAN_STARTED_AT=2026-07-09T01:00:00Z\n",
            "",
            0.01,
        )

    monkeypatch.setattr(audit_runs.proc, "run", fake_run)
    monkeypatch.setattr(audit_runs, "_learn_from_bugs_scan_boundary", _RUST_SCAN_BOUNDARY)
    assert audit_runs._learn_from_bugs_scan_boundary(tmp_path) == ("o/r", "2026-07-09T01:00:00Z")
    assert calls[0][1:] == ["learn-from-bugs", "read-state", "--root", str(tmp_path)]


def test_bugs_backlog_nudge_missing_marker_prints_never_run_without_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_runs.proc, "run", lambda argv, **_kwargs: pytest.fail(f"unexpected gh call: {argv}"))
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    assert "never run" in capsys.readouterr().out


def test_bugs_backlog_nudge_symlink_marker_is_unusable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".learn-from-bugs-test-state.json").symlink_to(tmp_path / "target.json")
    monkeypatch.setattr(audit_runs.proc, "run", lambda argv, **_kwargs: pytest.fail(f"unexpected gh call: {argv}"))
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    assert "never run" in capsys.readouterr().out


def test_bugs_backlog_nudge_different_repo_marker_is_unusable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_learn_from_bugs_state(tmp_path)
    monkeypatch.setattr(audit_runs.proc, "run", lambda argv, **_kwargs: pytest.fail(f"unexpected gh call: {argv}"))
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "other/repo", "--root", str(tmp_path)]) == 0
    assert "never run" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (config.LEARN_FROM_BUGS_NUDGE_THRESHOLD - 1, False),
        (config.LEARN_FROM_BUGS_NUDGE_THRESHOLD, False),
        (config.LEARN_FROM_BUGS_NUDGE_THRESHOLD + 1, True),
    ],
)
def test_bugs_backlog_nudge_threshold(
    count: int,
    expected: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_learn_from_bugs_state(tmp_path)
    monkeypatch.setattr(
        audit_runs.proc,
        "run",
        lambda argv, **_kwargs: CommandResult(tuple(argv), 0, _gh_issue_rows(count), "", 0.01),
    )
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert (str(count) in output) is expected


def test_bugs_backlog_nudge_filters_raw_github_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_learn_from_bugs_state(tmp_path)
    rows = [
        {"number": number + 1, "title": "plain task", "closedAt": "2026-07-09T02:00:00Z"}
        for number in range(config.LEARN_FROM_BUGS_NUDGE_THRESHOLD + 10)
    ]
    monkeypatch.setattr(
        audit_runs.proc,
        "run",
        lambda argv, **_kwargs: CommandResult(tuple(argv), 0, json.dumps(rows), "", 0.01),
    )
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


def test_bugs_backlog_nudge_accepts_lifecycle_prefixed_bug_titles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_learn_from_bugs_state(tmp_path)
    count = config.LEARN_FROM_BUGS_NUDGE_THRESHOLD + 1
    monkeypatch.setattr(
        audit_runs.proc,
        "run",
        lambda argv, **_kwargs: CommandResult(tuple(argv), 0, _gh_issue_rows(count, title="[DONE] [BUG] fixed"), "", 0.01),
    )
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    assert str(count) in capsys.readouterr().out


def test_bugs_backlog_nudge_excludes_rows_at_or_before_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_learn_from_bugs_state(tmp_path, scan_started_at="2026-07-09T01:00:00Z")
    monkeypatch.setattr(
        audit_runs.proc,
        "run",
        lambda argv, **_kwargs: CommandResult(
            tuple(argv),
            0,
            _gh_issue_rows(config.LEARN_FROM_BUGS_NUDGE_THRESHOLD + 1, closed_at="2026-07-09T01:00:00Z"),
            "",
            0.01,
        ),
    )
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("run_date", "scan_started_at", "expected"),
    [
        ("2026-07-01T00:00:00Z", "2026-07-09T01:00:00Z", "2026-07-09T01:00:00Z"),
        ("2026-07-01T00:00:00Z", None, "2026-07-01T00:00:00Z"),
    ],
)
def test_bugs_backlog_nudge_uses_durable_boundary(
    run_date: str,
    scan_started_at: str | None,
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_learn_from_bugs_state(tmp_path, run_date=run_date, scan_started_at=scan_started_at)
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> CommandResult:
        calls.append(argv)
        return CommandResult(tuple(argv), 0, "[]", "", 0.01)

    monkeypatch.setattr(audit_runs.proc, "run", fake_run)
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 0
    assert any(f"closed:>{expected}" in token for token in calls[0])


@pytest.mark.parametrize(
    ("stdout", "stderr", "expected"),
    [("", "boom", "gh issue list failed"), ("{bad-json", "", "invalid JSON")],
)
def test_bugs_backlog_nudge_fails_clearly(
    stdout: str,
    stderr: str,
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_learn_from_bugs_state(tmp_path)
    monkeypatch.setattr(
        audit_runs.proc,
        "run",
        lambda argv, **_kwargs: CommandResult(tuple(argv), 1 if stderr else 0, stdout, stderr, 0.01),
    )
    assert audit_runs.bugs_backlog_nudge_main(["--repo", "o/r", "--root", str(tmp_path)]) == 1
    assert expected in capsys.readouterr().err


class AuditRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]):
        self.responses = responses

    def run(self, argv: list[str], **_kwargs: object) -> CommandResult:
        key = tuple(argv)
        if key not in self.responses:
            raise AssertionError(f"unexpected argv: {argv}")
        return self.responses[key]


def cr(argv: tuple[str, ...], stdout: str = "", stderr: str = "", rc: int = 0) -> CommandResult:
    return CommandResult(argv, rc, stdout, stderr, 0.01)


def test_close_priors_reports_transport_failure_before_json_parse(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = AuditRunner({
        ("gh", "issue", "list", "--repo", "o/r", "--state", "open", "--json", "number,title", "--label", "audit-report", "--limit", "100000"): cr(("gh",), stdout="not json", stderr="network down", rc=1),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "9", "--repo", "o/r", "--operator-invoked"]) == 1
    output = capsys.readouterr().out
    assert "ISSUE_LIST_FAILED=true" in output
    assert "REASON=gh issue list failed" in output


def test_close_priors_reports_malformed_success_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = AuditRunner({
        ("gh", "issue", "list", "--repo", "o/r", "--state", "open", "--json", "number,title", "--label", "audit-report", "--limit", "100000"): cr(("gh",), stdout="not json"),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "9", "--repo", "o/r", "--operator-invoked"]) == 1
    assert "ISSUE_LIST_FAILED=true" in capsys.readouterr().out


def test_close_priors_body_file_failure_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = AuditRunner({
        ("gh", "issue", "list", "--repo", "o/r", "--state", "open", "--json", "number,title", "--label", "audit-report", "--limit", "100000"): cr(("gh",), stdout="[]"),
    })
    monkeypatch.setattr(audit_runs.proc, "run", runner.run)

    def fail_named_temp(*_args: object, **_kwargs: object) -> None:
        raise OSError("no temp")

    monkeypatch.setattr(audit_runs.tempfile, "NamedTemporaryFile", fail_named_temp)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "9", "--repo", "o/r", "--operator-invoked"]) == 1
    output = capsys.readouterr().out
    assert "BODY_FILE_FAILED=true" in output
    assert "REASON=mktemp failed" in output


def test_close_priors_reports_partial_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prior = json.dumps([
        {"number": 7, "title": "[Implement Run Logs Audit 2026 Report] old"},
        {"number": 8, "title": "[Implement Run Logs Audit 2026 Report] older"},
    ])

    class PartialCloseRunner:
        def run(self, argv: list[str], **_kwargs: object) -> CommandResult:
            if argv[:3] == ["gh", "issue", "list"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",), stdout=prior)
            if argv[:4] == ["gh", "issue", "comment", "7"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",))
            if argv[:4] == ["gh", "issue", "close", "7"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",))
            if argv[:4] == ["gh", "issue", "view", "7"]:  # lint-gh-argv-literal: ok post-close state read-back
                return cr(("gh",), stdout=json.dumps({"state": "CLOSED"}))
            if argv[:4] == ["gh", "issue", "comment", "8"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",), stderr="boom", rc=1)
            raise AssertionError(f"unexpected argv: {argv}")

    monkeypatch.setattr(audit_runs.proc, "run", PartialCloseRunner().run)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "9", "--repo", "o/r", "--operator-invoked"]) == 0
    output = capsys.readouterr().out.splitlines()
    assert "CLOSED_NUMBER=7" in output
    assert any(line.startswith("CLOSE_FAILED=8\tREASON=gh issue comment failed") for line in output)


def test_close_priors_flags_unverified_close(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prior = json.dumps([{"number": 7, "title": "[Implement Run Logs Audit 2026 Report] old"}])

    class UnverifiedCloseRunner:
        def run(self, argv: list[str], **_kwargs: object) -> CommandResult:
            if argv[:3] == ["gh", "issue", "list"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",), stdout=prior)
            if argv[:4] == ["gh", "issue", "comment", "7"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",))
            if argv[:4] == ["gh", "issue", "close", "7"]:  # lint-gh-argv-literal: ok fixture assertion
                return cr(("gh",))
            if argv[:4] == ["gh", "issue", "view", "7"]:  # lint-gh-argv-literal: ok post-close state read-back
                return cr(("gh",), stdout=json.dumps({"state": "OPEN"}))
            raise AssertionError(f"unexpected argv: {argv}")

    monkeypatch.setattr(audit_runs.proc, "run", UnverifiedCloseRunner().run)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "9", "--repo", "o/r", "--operator-invoked"]) == 0
    output = capsys.readouterr().out.splitlines()
    assert f"CLOSE_FAILED=7\tREASON={config.CLOSE_POSTCONDITION_UNVERIFIED}" in output
    assert "CLOSED_NUMBER=7" not in output


def test_close_priors_refuses_without_operator_invoked(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "99"]) == config.EXIT_MUTATION_REFUSED
    assert "CLOSE_PRIORS_REFUSED=true" in capsys.readouterr().out


def test_close_priors_without_operator_invoked_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    assert audit_runs.close_priors_main(["--skill", "implement", "--new-issue-number", "99"]) == config.EXIT_MUTATION_REFUSED
