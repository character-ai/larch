# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for /issue Python helper entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import issue_create
import proc

SKILL_PATH = Path(__file__).resolve().parents[1] / "skills/issue/SKILL.md"


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def test_parse_input_oos_and_malformed_body_file(tmp_path: Path, capsys: Any) -> None:
    input_file = tmp_path / "items.md"
    input_file.write_text(
        "### OOS_1: first\n"
        "- **Description**: body\n"
        "### Ambiguous\n"
        "pending body\n"
        "### OOS_2: second\n"
        "- **Description**: ok\n"
        "- **Reviewer**: R\n"
        "- **Vote tally**: YES=1\n"
        "- **Phase**: review\n"
        "### title only\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    assert issue_create.parse_input_main(["--input-file", str(input_file), "--output-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    assert "ITEMS_TOTAL=4" in out
    assert "ITEM_1_BODY_FILE=" in out
    assert "ITEM_1_MALFORMED=true" in out
    assert "ITEM_3_REVIEWER=R" in out
    assert "ITEM_4_TITLE=title only" in out
    assert "ITEM_4_BODY_FILE=" not in out
    assert (out_dir / "item-1-body.txt").read_text(encoding="utf-8") == "body"


def test_allocate_candidates_union_credit() -> None:
    rows = (
        "CAND 1 10 dup high\n"
        "CAND 1 11 dup medium\n"
        "CAND 2 10 dup low\n"
        "CAND 2 12 dep high"
    )
    assert issue_create.allocate_candidates(2, rows) == [10, 11, 12]


def test_create_one_dry_run_redacts(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body crsr_0123456789abcdefghijklmnopqrstuvwxyzABCDEF", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "label", "list"]:
            return _result(argv, stdout="bug\n")
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(
        [
            "--title",
            "[OOS] leaking crsr_0123456789abcdefghijklmnopqrstuvwxyzABCDEF",
            "--title-prefix",
            "[OOS]",
            "--label",
            "bug",
            "--body-file",
            str(body),
            "--repo",
            "owner/repo",
            "--dry-run",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY_RUN=true" in out
    assert "DRY_RUN_LABELS=bug" in out
    assert "[OOS] leaking <REDACTED-TOKEN>" in out
    assert "crsr_0123456789" not in out


def test_create_one_success_json(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(argv, stdout=json.dumps({"id": 99, "number": 5, "url": "https://x/issues/5"}))
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"]) == 0
    out = capsys.readouterr().out
    assert "ISSUE_NUMBER=5" in out
    assert "ISSUE_ID=99" in out
    assert "ISSUE_TITLE=T" in out


def test_add_blocked_by_retry_idempotent(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 422 duplicate dependency")

    sleeps: list[float] = []
    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    rc = issue_create.add_blocked_by_main(
        ["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"],
        sleep_fn=record_sleep,
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in out
    assert not sleeps
    assert len(calls) == 2


def test_list_issues_filters_archival(monkeypatch: Any, capsys: Any) -> None:
    payload = [
        {"number": 1, "title": "Keep\tTitle", "state": "open", "html_url": "u1"},
        {"number": 2, "title": "Research spike", "state": "open", "html_url": "u2"},
        {"number": 3, "title": "Closed", "state": "closed", "closed_at": "2099-01-01T00:00:00Z", "html_url": "u3"},
        {"number": 4, "title": "PR", "state": "open", "pull_request": {}, "html_url": "u4"},
    ]

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "api", "--paginate"]:
            return _result(argv, stdout=json.dumps(payload))
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.list_issues_main(["--repo", "o/r", "--closed-window-days", "90"]) == 0
    out = capsys.readouterr().out
    assert "LIST_STATUS=ok" in out
    assert "1\tKeep Title\topen\tu1" in out
    assert "2\t" not in out
    assert "3\tClosed\tclosed\tu3" in out
    assert "4\t" not in out


def test_parse_input_write_failure_returns_one(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    input_file = tmp_path / "items.md"
    input_file.write_text("### OOS_1: first\n- **Description**: body\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fail_write(*_: object, **__: object) -> None:
        raise OSError(13, "permission denied")

    monkeypatch.setattr(Path, "write_text", fail_write)
    assert issue_create.parse_input_main(["--input-file", str(input_file), "--output-dir", str(out_dir)]) == 1
    assert "failed to write body file" in capsys.readouterr().err


def test_fetch_issue_details_success_and_validation(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    payload = {
        "number": 9,
        "title": "T",
        "body": "body",
        "state": "open",
        "url": "https://x/issues/9",
        "comments": [],
    }

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "view"]:
            return _result(argv, stdout=json.dumps(payload))
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    out_path = tmp_path / "corpus.md"
    assert issue_create.fetch_issue_details_main(["--numbers", "9", "--output", str(out_path), "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    assert "FETCH_STATUS_9=ok" in out
    assert "<external_issue_9>" in out_path.read_text(encoding="utf-8")
    assert issue_create.fetch_issue_details_main(["--numbers", "9", "--output", str(out_path), "--max-comments", "x"]) == 1


def test_cleanup_failed_closes_orphan(monkeypatch: Any, capsys: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "close"]:
            return _result(argv)
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.cleanup_failed_main(["--issue-number", "7", "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    assert "CLOSED=true" in out
    assert "ISSUE=7" in out


def test_allocate_candidates_rejects_over_cap(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr("issue_create.sys.stdin", type("S", (), {"read": lambda _self: ""})())
    assert issue_create.allocate_candidates_main(["--total-items", "31"]) == 0
    assert "exceeds 30" in capsys.readouterr().err


def test_add_blocked_by_404_no_retry(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 404: Not Found")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED_BY_FAILED=true" in out
    assert len(calls) == 2


def test_create_one_redaction_failure_exits_three(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def boom(_text: str) -> str:
        raise RuntimeError("redact failed")

    monkeypatch.setattr(issue_create, "redact_outbound", boom)
    rc = issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "ISSUE_FAILED=true" in out
    assert "ISSUE_ERROR=redaction:" in out


def test_skill_pins_intra_batch_dependency_contract() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "N_NON_MALFORMED >= 2",
        "skip `issue fetch-issue-details` entirely",
        "Empty-CANDIDATES + multi-item path",
        "no-external-refs",
        "FETCH_STATUS_",
        "intra-batch-deps-file FILE",
        "Caller-supplied intra-batch deps merge",
        "no-dep-llm",
    )
    for needle in needles:
        assert needle in text, needle


def test_skill_pins_blocked_by_issue_contract() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "--blocked-by-issue N",
        "--no-dedup and --blocked-by-issue are mutually exclusive",
        "--blocked-by-issue requires --input-file (batch mode)",
        "--blocked-by-issue must be a positive integer",
        'gh api "/repos/$REPO/issues/$BLOCKED_BY_ISSUE"',
        "pull_request != null",
        "Caller-supplied --blocked-by-issue merge",
        "Carve-out for --blocked-by-issue",
        "--blocker-id $BLOCKED_BY_ISSUE_ID",
    )
    for needle in needles:
        assert needle in text, needle


def test_write_sentinel_stderr_only(tmp_path: Path, capsys: Any) -> None:
    target = tmp_path / "sentinel.env"
    rc = issue_create.write_sentinel_main(
        ["--path", str(target), "--issues-created", "1", "--issues-deduplicated", "2", "--issues-failed", "0"],
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == "WROTE=true\n"
    assert "ISSUES_CREATED=1" in target.read_text(encoding="utf-8")
