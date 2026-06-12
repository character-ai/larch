# pyright: reportUnusedCallResult=false
"""Tests for tracking_issue.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cli
import config
import tracking_issue
from errors import ShipError
from proc import CommandResult


from test_support import RecordingRunner


def _quiet_noop(*, argv0: str | None = None) -> None:
    _ = argv0


def test_link_pr_closes_appends() -> None:
    body = "Summary\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert "Closes #42" in linked


def test_link_pr_closes_idempotent() -> None:
    body = "Summary\n\nCloses #42\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert linked == body


def test_link_pr_closes_ignores_prose_mentions() -> None:
    body = "Summary says Closes #42 should be added as a footer.\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_mermaid_mentions() -> None:
    body = "```mermaid\nflowchart LR\n  A[Closes #42] --> B\n```\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_fenced_exact_line() -> None:
    body = "```text\nCloses #42\n```\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_non_footer_exact_line() -> None:
    body = "Closes #42\n\n## Test plan\n\n- [x] passed\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_no_prefix_collision() -> None:
    body = "Summary\n\nCloses #421\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert "Closes #421" in linked
    assert "Closes #42\n" in linked


def test_rename_strips_legacy_prefix() -> None:
    runner = RecordingRunner()
    title = "[IN PROGRESS] [DONE] My feature"
    new = tracking_issue.rename(
        runner,
        "1",
        "done",
        repo="o/r",
        current_title=title,
    )
    assert new.startswith(config.TRACKING_ISSUE_PREFIX_BY_STATE["done"])
    assert "[IN PROGRESS]" not in new


def test_append_comment_rejects_invalid_lifecycle_marker() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="invalid lifecycle marker"):
        tracking_issue.append_comment(
            runner,
            "1",
            "body",
            repo="o/r",
            lifecycle_marker="bad--marker",
        )


def test_append_comment_accepts_colon_lifecycle_marker() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "issue", "comment", "1"), 0, "", "", 0.01),
        ],
    )
    tracking_issue.append_comment(
        runner,
        "1",
        "body",
        repo="o/r",
        lifecycle_marker="pr:opened",
    )
    assert runner.calls[-1][1:3] == ["issue", "comment"]


def test_upsert_summary_patches_existing_comment() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":12,"body":"<!-- larch:final-summary -->\\nold"}]',
                "",
                0.01,
            ),
            CommandResult(("gh", "api"), 0, "", "", 0.01),
        ],
    )
    tracking_issue.upsert_summary(runner, "1", "new body", repo="o/r")
    assert runner.calls[-1][1] == "api"
    assert "PATCH" in runner.calls[-1]


def test_upsert_token_report_truncates_title_prefix() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                "[]",
                "",
                0.01,
            ),
            CommandResult(("gh", "issue", "comment", "1"), 0, "", "", 0.01),
        ],
    )
    long_body = "x" * 400
    tracking_issue.upsert_token_report(runner, "1", long_body, repo="o/r")
    posted = runner.calls[-1]
    assert "comment" in posted


def test_upsert_token_report_rename_matrix() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":5,"body":"<!-- larch:token-report -->\\nold"}]',
                "",
                0.01,
            ),
            CommandResult(("gh", "api"), 0, "", "", 0.01),
        ],
    )
    tracking_issue.upsert_token_report(runner, "1", "updated", repo="o/r")
    assert runner.calls[-1][1] == "api"
    assert "PATCH" in runner.calls[-1]


def test_rename_truncates_after_redaction() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "issue", "edit", "1"), 0, "", "", 0.01)],
    )
    long_tail = "x" * 300
    title = f"[DESIGNING] {long_tail}"
    new = tracking_issue.rename(
        runner,
        "1",
        "implementing",
        repo="o/r",
        current_title=title,
    )
    assert len(new) <= config.TRACKING_TITLE_MAX_LEN
    edit_argv = runner.calls[-1]
    title_arg_index = edit_argv.index("--title") + 1
    assert len(edit_argv[title_arg_index]) <= config.TRACKING_TITLE_MAX_LEN


def test_rename_skips_edit_when_redacted_canonical_current_matches() -> None:
    runner = RecordingRunner()
    long_tail = "x" * 300
    title = f"[IMPLEMENTING] {long_tail}"
    new = tracking_issue.rename(
        runner,
        "1",
        "implementing",
        repo="o/r",
        current_title=title,
    )
    assert len(new) <= config.TRACKING_TITLE_MAX_LEN
    assert not runner.calls


def test_rename_raises_on_truncated_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()

    def fake_redact(_text: str) -> str:
        return "x [content truncated — safety]"

    monkeypatch.setattr(tracking_issue.redact, "redact", fake_redact)
    with pytest.raises(ShipError, match="redaction failed"):
        _ = tracking_issue.rename(
            runner,
            "1",
            "done",
            repo="o/r",
            current_title="[DESIGNING] title",
        )


def test_rename_public_adapter_wraps_cli_failure() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="invalid --state"):
        _ = tracking_issue.rename(
            runner,
            "1",
            "bogus",
            repo="o/r",
            current_title="[DESIGNING] title",
        )


def test_strip_lifecycle_prefix_strips_exactly_one() -> None:
    assert tracking_issue.strip_lifecycle_prefix("[PLANNED] [DONE] Work") == "[DONE] Work"
    assert tracking_issue.strip_lifecycle_prefix("Work") == "Work"


def test_read_main_sentinel_valid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "parent-issue.md"
    path.write_text("\ufeffISSUE_NUMBER=123\r\nRUN_ID=run-1\r\nADOPTED=true\r\n", encoding="utf-8")
    rc = tracking_issue.read_main(["--sentinel", str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISSUE_NUMBER=123" in out
    assert "RUN_ID=run-1" in out
    assert "ADOPTED=true" in out


def test_read_main_prompt_validates_out_dir_before_write(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "missing"
    rc = tracking_issue.read_main(["--prompt", "hello", "--out-dir", str(missing)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert not (missing / "task.md").exists()


def test_read_issue_filters_marker_comments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "api"), 0, "body", "", 0.01),
            CommandResult(
                ("gh", "api"),
                0,
                '{"id":1,"body":"<!-- larch:metadata v1 runid=x -->\\nskip"}'
                '\n{"id":2,"body":"keep"}',
                "",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    rc = tracking_issue.read_main(["--issue", "9", "--repo", "o/r", "--out-dir", str(tmp_path)])
    _ = capsys.readouterr()
    content = (tmp_path / "task.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "metadata" not in content
    assert '<external_issue_comment id="2">' in content


@pytest.mark.parametrize(
    "marker_body",
    [
        "<!-- larch:lifecycle-marker:pr-opened -->\nskip",
        "<!-- larch:diagrams v1 -->\nskip",
        "<!-- larch:diagrams v1 runid=run1 -->\nskip",
        "<!-- larch:plan v1 runid=run1 -->\nskip",
        "<!-- larch:token-report v1 runid=run1 -->\nskip",
        "<!-- larch:final-summary v1 runid=run1 -->\nskip",
        "<!-- larch:implement-anchor v1 issue=1 -->\nskip",
    ],
)
def test_read_issue_filters_all_managed_marker_families(
    marker_body: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "api"), 0, "body", "", 0.01),
            CommandResult(
                ("gh", "api"),
                0,
                f'{{"id":1,"body":{json.dumps(marker_body)}}}\n{{"id":2,"body":"keep"}}',
                "",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    rc = tracking_issue.read_main(["--issue", "9", "--repo", "o/r", "--out-dir", str(tmp_path)])
    _ = capsys.readouterr()
    content = (tmp_path / "task.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "skip" not in content
    assert '<external_issue_comment id="2">' in content


def test_create_issue_cli_rejects_newline_only_body(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("\n\n", encoding="utf-8")
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.create_issue_main(["--title", "title", "--body-file", str(body), "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "ERROR=empty body" in out


def test_append_comment_cli_rejects_newline_only_body(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("\r\n", encoding="utf-8")
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.append_comment_main(["--issue", "1", "--repo", "o/r", "--body-file", str(body)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "ERROR=empty body" in out


def test_create_issue_gh_stderr_redacts_token_in_failure_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    secret = "ghp_" + "a" * 36
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "issue", "create"), 1, "", f"failed with {secret}", 0.01)],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.create_issue_main(["--title", "title", "--body-file", str(body), "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAILED=true" in out
    assert secret not in out


def test_cli_failure_newlines_emit_flat_failure_envelope(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> tracking_issue.CreateIssueOutput:
        raise tracking_issue.CliFailure("line one\nline two", 2)

    monkeypatch.setattr(tracking_issue, "_create_issue_cli", fail)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.create_issue_main(["--title", "title", "--body-file", "body.md", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 2
    assert out == "FAILED=true\nERROR=line one line two\n"


def test_create_issue_main_unexpected_exception_emits_failure_envelope(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> tracking_issue.CreateIssueOutput:
        raise OSError("disk\nboom")

    monkeypatch.setattr(tracking_issue, "_create_issue_cli", fail)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.create_issue_main(["--title", "title", "--body-file", "body.md", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 2
    assert out == "FAILED=true\nERROR=unexpected OSError: disk boom\n"


def test_upsert_summary_main_unexpected_exception_uses_stderr_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body", encoding="utf-8")

    def fail(*_args: object, **_kwargs: object) -> tracking_issue.UpsertSummaryOutput:
        raise ValueError("bad\nvalue")

    monkeypatch.setattr(tracking_issue, "_upsert_summary_cli", fail)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", "<!-- larch:plan v1 runid=run1 -->", "--content-file", str(content), "--repo", "o/r"]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert captured.err == "FAILED=true\nERROR=unexpected ValueError: bad value\n"


def test_append_comment_cli_requires_issuecomment_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[CommandResult(("gh", "issue", "comment"), 0, "https://example.test/issues/1", "", 0.01)])
    monkeypatch.setattr(tracking_issue, "proc", runner)
    rc = tracking_issue.append_comment_main(["--issue", "1", "--repo", "o/r", "--body-file", str(body)])
    assert rc == 2


def test_mark_false_positive_idempotent_skips_edit() -> None:
    runner = RecordingRunner()
    result = tracking_issue.mark_false_positive(
        runner,
        "1",
        repo="o/r",
        current_title="[FALSE-POSITIVE] [IMPLEMENTING] work",
    )
    assert result.marked is False
    assert not runner.calls


def test_cli_registry_tracking_issue_read_sentinel(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "parent-issue.md"
    path.write_text("ISSUE_NUMBER=5\nRUN_ID=run\nADOPTED=false\n", encoding="utf-8")
    rc = cli.main(["tracking-issue", "read", "--sentinel", str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISSUE_NUMBER=5" in out
