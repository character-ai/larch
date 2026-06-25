# pyright: reportUnusedCallResult=false
"""Tests for tracking_issue.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
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


def _tracking_issue_subprocess(
    args: list[str],
    tmp_path: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(tmp_path)
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    if extra_env is not None:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "python/cli.py", "tracking-issue", *args],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _tracking_issue_subprocess_redirected(
    args: list[str],
    tmp_path: Path,
    stdout_path: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(tmp_path)
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    if extra_env is not None:
        env.update(extra_env)
    with stdout_path.open("w", encoding="utf-8") as stdout:
        return subprocess.run(
            [sys.executable, "python/cli.py", "tracking-issue", *args],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            stdout=stdout,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )


def _tracking_issue_subprocess_stderr_redirected(
    args: list[str],
    tmp_path: Path,
    stderr_path: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(tmp_path)
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    if extra_env is not None:
        env.update(extra_env)
    with stderr_path.open("w", encoding="utf-8") as stderr:
        return subprocess.run(
            [sys.executable, "python/cli.py", "tracking-issue", *args],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            stdout=subprocess.PIPE,
            stderr=stderr,
            check=False,
            env=env,
        )


def test_link_pr_closes_appends() -> None:
    body = "Summary\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert "Closes #42" in linked


def test_link_pr_closes_idempotent() -> None:
    body = "Summary\n\nCloses #42\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked == body


def test_link_pr_closes_ignores_prose_mentions() -> None:
    body = "Summary says Closes #42 should be added as a footer.\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_mermaid_mentions() -> None:
    body = "```mermaid\nflowchart LR\n  A[Closes #42] --> B\n```\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_fenced_exact_line() -> None:
    body = "```text\nCloses #42\n```\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_ignores_non_footer_exact_line() -> None:
    body = "Closes #42\n\n## Test plan\n\n- [x] passed\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
    assert linked.count("Closes #42") == 2
    assert linked.rstrip().endswith("Closes #42")


def test_link_pr_closes_no_prefix_collision() -> None:
    body = "Summary\n\nCloses #421\n"
    linked = tracking_issue.link_pr_closes(body=body, issue_number=42)
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


def test_read_main_rejects_malformed_sentinel(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "parent-issue.md"
    path.write_text("ISSUE_NUMBER=abc\nRUN_ID=run\nADOPTED=false\n", encoding="utf-8")
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.read_main(["--sentinel", str(path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "malformed-value-omitted" in out


def test_read_main_prompt_honors_total_cap_override(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.read_main(
        ["--prompt", "abcdef", "--out-dir", str(tmp_path), "--max-total-chars", "5"]
    )
    _ = capsys.readouterr()
    content = (tmp_path / "task.md").read_text(encoding="utf-8")
    assert rc == 0
    assert content == "abcde\n[TRUNCATED — task-file-total exceeded 5 chars]\n"


def test_read_issue_prompt_append_failure_maps_to_read_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "issue", "comment", "9"), 1, "", "boom", 0.01)],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.read_main(["--issue", "9", "--prompt", "note", "--repo", "o/r", "--out-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAILED=true" in out
    assert "append-comment failed" in out
    assert not (tmp_path / "task.md").exists()


def test_read_issue_rejects_newline_only_prompt_before_append(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.read_main(["--issue", "9", "--prompt", "\n", "--repo", "o/r", "--out-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAILED=true" in out
    assert "ERROR=append-comment failed: empty body" in out
    assert not runner.calls
    assert not (tmp_path / "task.md").exists()


def test_read_issue_prompt_append_redaction_failure_maps_to_read_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_append(*_args: object, **_kwargs: object) -> tuple[str, str]:
        raise tracking_issue.RedactionFailure("redaction failed for tracking-issue comment")

    monkeypatch.setattr(tracking_issue, "_append_comment_cli", fail_append)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.read_main(["--issue", "9", "--prompt", "note", "--repo", "o/r", "--out-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAILED=true" in out
    assert "ERROR=append-comment failed: redaction failed" in out
    assert not (tmp_path / "task.md").exists()


def test_read_issue_prompt_success_appends_then_renders_task(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "issue", "comment", "9"),
                0,
                "https://github.com/o/r/issues/9#issuecomment-44",
                "",
                0.01,
            ),
            CommandResult(("gh", "api"), 0, "issue body\n", "", 0.01),
            CommandResult(
                ("gh", "api"),
                0,
                '{"id":11,"body":"kept comment"}\n',
                "",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.read_main(
        ["--issue", "9", "--prompt", "operator prompt", "--repo", "o/r", "--out-dir", str(tmp_path)]
    )
    out = capsys.readouterr().out
    task_file = tmp_path / "task.md"

    assert rc == 0
    assert "ISSUE_NUMBER=9" in out
    assert "TASK_SOURCE=issue-plus-prompt" in out
    assert f"TASK_FILE={task_file}" in out
    assert runner.calls[0][1:3] == ["issue", "comment"]
    assert runner.calls[1][:2] == ["gh", "api"]
    assert runner.calls[2][:2] == ["gh", "api"]
    assert task_file.read_text(encoding="utf-8").endswith(
        '<external_issue_comment id="11">\nkept comment\n</external_issue_comment>\n\n\noperator prompt\n'
    )


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


def test_create_issue_cli_rejects_empty_title_before_gh(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.create_issue_main(["--title", "", "--body-file", str(body), "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "ERROR=empty title" in out
    assert not runner.calls


def test_create_issue_validates_body_file_before_repo_resolution(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.create_issue_main(["--title", "title", "--body-file", "missing.md"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "body file not found" in out
    assert not runner.calls


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


def test_append_comment_validates_issue_before_repo_resolution(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.append_comment_main(["--issue", "abc", "--body-file", str(body)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid issue" in out
    assert not runner.calls


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


@pytest.mark.parametrize(
    "argv",
    [
        ["create-issue", "--title", "title", "--body-file", "{body}", "--repo", "o/r"],
        ["append-comment", "--issue", "1", "--body-file", "{body}", "--repo", "o/r"],
    ],
)
def test_tracking_issue_write_verbs_emit_exit_3_stdout_envelope_on_redaction_failure(
    argv: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    runner = RecordingRunner()

    def fake_redact(_text: str) -> str:
        return "[content truncated for test]"

    resolved = [arg.replace("{body}", str(body)) for arg in argv]
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.redact, "redact", fake_redact)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = cli.main(["tracking-issue", *resolved])
    captured = capsys.readouterr()
    assert rc == 3
    assert captured.out.startswith("FAILED=true\nERROR=redaction: redaction failed for tracking-issue")
    assert captured.err == ""
    assert not runner.calls


@pytest.mark.parametrize(
    "argv",
    [
        ["rename", "--issue", "1", "--state", "done", "--repo", "o/r"],
        ["mark-false-positive", "--issue", "1", "--repo", "o/r"],
    ],
)
def test_tracking_issue_title_write_verbs_emit_exit_3_stdout_envelope_on_redaction_failure(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(responses=[CommandResult(("gh", "issue", "view", "1"), 0, "[DESIGNING] title\n", "", 0.01)])

    def fake_redact(_text: str) -> str:
        return "[content truncated for test]"

    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.redact, "redact", fake_redact)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = cli.main(["tracking-issue", *argv])
    captured = capsys.readouterr()
    assert rc == 3
    assert captured.out.startswith("FAILED=true\nERROR=redaction: redaction failed for tracking-issue title")
    assert captured.err == ""
    assert len(runner.calls) == 1


def test_upsert_summary_emit_exit_3_stderr_envelope_on_redaction_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("-----BEGIN PRIVATE KEY-----\nsecret\n", encoding="utf-8")
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", "<!-- larch:plan v1 runid=run1 -->", "--content-file", str(content), "--repo", "o/r"]
    )
    captured = capsys.readouterr()
    assert rc == 3
    assert captured.out == ""
    assert captured.err.startswith("FAILED=true\nERROR=redaction: redaction failed for tracking-issue summary")
    assert not runner.calls


def test_append_comment_cli_requires_issuecomment_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[CommandResult(("gh", "issue", "comment"), 0, "https://example.test/issues/1", "", 0.01)])
    monkeypatch.setattr(tracking_issue, "proc", runner)
    rc = tracking_issue.append_comment_main(["--issue", "1", "--repo", "o/r", "--body-file", str(body)])
    assert rc == 2


def test_rename_validates_state_before_issue_fetch(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.rename_main(["--issue", "1", "--state", "bogus", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid --state" in out
    assert not runner.calls


def test_mark_false_positive_validates_issue_before_issue_fetch(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.mark_false_positive_main(["--issue", "abc", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "invalid issue" in out
    assert not runner.calls


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


def test_upsert_summary_validates_content_file_before_repo_resolution(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", "<!-- larch:plan v1 runid=run1 -->", "--content-file", "missing.md"]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert "content file not found" in captured.err
    assert not runner.calls


def test_upsert_summary_cli_creates_comment_when_marker_absent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "api"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "issue", "comment", "1"),
                0,
                "https://github.com/o/r/issues/1#issuecomment-22",
                "",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", "<!-- larch:plan v1 runid=run1 -->", "--content-file", str(content), "--repo", "o/r"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMENT_ID=22" in out
    assert "UPDATED=false" in out


def test_upsert_summary_cli_updates_existing_comment_with_exact_body(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body\n", encoding="utf-8")
    marker = "<!-- larch:plan v1 runid=run1 -->"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                json.dumps([{"id": 33, "body": f"{marker}\nold"}]),
                "",
                0.01,
            ),
        ],
    )
    patched: dict[str, object] = {}

    def fake_patch(
        _runner: RecordingRunner,
        comment_id: int,
        body: str,
        *,
        repo: str,
        cwd: str | None = None,
    ) -> CommandResult:
        patched.update({"comment_id": comment_id, "body": body, "repo": repo, "cwd": cwd})
        return CommandResult(("gh", "api"), 0, '{"html_url":"https://github.com/o/r/issues/1#issuecomment-33"}', "", 0.01)

    monkeypatch.setattr(tracking_issue.gh, "issue_comment_patch", fake_patch)
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", marker, "--content-file", str(content), "--repo", "o/r"]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "COMMENT_ID=33" in captured.out
    assert "COMMENT_URL=https://github.com/o/r/issues/1#issuecomment-33" in captured.out
    assert "UPDATED=true" in captured.out
    assert patched == {"comment_id": 33, "body": f"{marker}\n\nbody", "repo": "o/r", "cwd": None}


def test_upsert_summary_cli_rejects_duplicate_existing_comments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body", encoding="utf-8")
    marker = "<!-- larch:plan v1 runid=run1 -->"
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                json.dumps([{"id": 33, "body": marker}, {"id": 44, "body": marker}]),
                "",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", marker, "--content-file", str(content), "--repo", "o/r"]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert captured.out == ""
    assert "FAILED=true" in captured.err
    assert "ERROR=multiple summary comments found for marker (ids: 33,44)" in captured.err


def test_upsert_summary_cli_comment_id_bypasses_marker_search(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body", encoding="utf-8")
    marker = "<!-- larch:plan v1 runid=run1 -->"
    runner = RecordingRunner(strict=True)
    patched: dict[str, object] = {}

    def fake_patch(
        _runner: RecordingRunner,
        comment_id: int,
        body: str,
        *,
        repo: str,
        cwd: str | None = None,
    ) -> CommandResult:
        patched.update({"comment_id": comment_id, "body": body, "repo": repo, "cwd": cwd})
        return CommandResult(("gh", "api"), 0, "https://github.com/o/r/issues/1#issuecomment-55", "", 0.01)

    monkeypatch.setattr(tracking_issue.gh, "issue_comment_patch", fake_patch)
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = tracking_issue.upsert_summary_main(
        ["--issue", "1", "--marker", marker, "--content-file", str(content), "--repo", "o/r", "--comment-id", "55"]
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert "COMMENT_ID=55" in captured.out
    assert "COMMENT_URL=https://github.com/o/r/issues/1#issuecomment-55" in captured.out
    assert "UPDATED=true" in captured.out
    assert patched == {"comment_id": 55, "body": f"{marker}\n\nbody", "repo": "o/r", "cwd": None}
    assert not runner.calls


def test_tracking_issue_read_missing_value_usage_visible_under_quiet(tmp_path: Path) -> None:
    result = _tracking_issue_subprocess(["read", "--issue"], tmp_path)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "tracking-issue read: error: --issue requires a value" in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        ["read", "--issue", "abc", "--out-dir", "{tmp}"],
        ["read", "--issue", "1"],
        ["read", "--sentinel", "{sentinel}", "--out-dir", "{tmp}"],
    ],
)
def test_tracking_issue_read_shell_level_failures_emit_stdout_envelope(
    args: list[str],
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "parent-issue.md"
    sentinel.write_text("ISSUE_NUMBER=1\nRUN_ID=run\nADOPTED=true\n", encoding="utf-8")
    resolved = [
        arg.replace("{tmp}", str(tmp_path)).replace("{sentinel}", str(sentinel))
        for arg in args
    ]
    result = _tracking_issue_subprocess(resolved, tmp_path)
    assert result.returncode == 1
    assert "FAILED=true" in result.stdout
    assert "ERROR=usage:" in result.stdout
    assert result.stderr == ""


def test_tracking_issue_write_usage_visible_under_quiet(tmp_path: Path) -> None:
    result = _tracking_issue_subprocess(["append-comment", "--issue", "1"], tmp_path)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "usage: tracking-issue append-comment" in result.stderr
    assert "the following arguments are required: --body-file" in result.stderr


@pytest.mark.parametrize(
    ("entrypoint", "argv"),
    [
        (tracking_issue.create_issue_main, ["--title", "title"]),
        (tracking_issue.append_comment_main, ["--issue", "1"]),
        (tracking_issue.rename_main, ["--issue", "1"]),
        (tracking_issue.mark_false_positive_main, []),
        (tracking_issue.upsert_summary_main, ["--issue", "1"]),
    ],
)
def test_tracking_issue_write_usage_initializes_quiet_before_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: Callable[[list[str]], int],
    argv: list[str],
) -> None:
    events: list[str] = []

    def fake_quiet_init(*, argv0: str | None = None) -> None:
        events.append(f"quiet:{argv0 or ''}")

    def fake_diagnostic(message: str) -> None:
        events.append(f"diagnostic:{message.splitlines()[0] if message else ''}")

    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", fake_quiet_init)
    monkeypatch.setattr(tracking_issue.logging_util, "diagnostic", fake_diagnostic)

    assert entrypoint(argv) == 1
    assert events[0].startswith("quiet:")
    assert any(event.startswith("diagnostic:usage: tracking-issue ") for event in events)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["create-issue", "--title", "title", "--body-file", "missing.md"], "body file not found"),
        (["append-comment", "--issue", "abc", "--body-file", "{body}"], "invalid issue"),
        (["rename", "--issue", "1", "--state", "bogus", "--repo", "o/r"], "invalid --state"),
        (["mark-false-positive", "--issue", "abc", "--repo", "o/r"], "invalid issue"),
    ],
)
def test_tracking_issue_write_non_usage_failures_emit_stdout_envelope(
    args: list[str],
    expected: str,
    tmp_path: Path,
) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    resolved = [arg.replace("{body}", str(body)) for arg in args]
    result = _tracking_issue_subprocess(resolved, tmp_path)
    assert result.returncode == 1
    assert "FAILED=true" in result.stdout
    assert f"ERROR={expected}" in result.stdout
    assert result.stderr == ""


def test_tracking_issue_read_success_kvs_reach_redirected_stdout_under_inherited_quiet(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "parent-issue.md"
    sentinel.write_text("ISSUE_NUMBER=5\nRUN_ID=run\nADOPTED=false\n", encoding="utf-8")
    stdout_path = tmp_path / "stdout.txt"
    result = _tracking_issue_subprocess_redirected(
        ["read", "--sentinel", str(sentinel)],
        tmp_path,
        stdout_path,
        extra_env={
            config.ENV_LARCH_QUIET_ACTIVE: "1",
            config.ENV_LARCH_QUIET_PID: str(os.getpid()),
        },
    )
    assert result.returncode == 0
    assert stdout_path.read_text(encoding="utf-8") == (
        "ISSUE_NUMBER=5\nRUN_ID=run\nADOPTED=false\n"
    )
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("args", "expected", "returncode"),
    [
        (
            ["upsert-summary", "--issue", "1", "--marker", "bad-marker", "--content-file", "{content}", "--repo", "o/r"],
            "invalid marker",
            1,
        ),
        (
            [
                "upsert-summary",
                "--issue",
                "1",
                "--marker",
                "<!-- larch:plan v1 runid=run1 -->",
                "--content-file",
                "{missing}",
                "--repo",
                "o/r",
            ],
            "content file not found",
            1,
        ),
        (
            [
                "upsert-summary",
                "--issue",
                "1",
                "--marker",
                "<!-- larch:plan v1 runid=run1 -->",
                "--content-file",
                "{content}",
                "--repo",
                "bad-repo",
            ],
            "invalid repo",
            1,
        ),
    ],
)
def test_upsert_summary_validation_failures_emit_stderr_under_inherited_quiet(
    args: list[str],
    expected: str,
    returncode: int,
    tmp_path: Path,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body", encoding="utf-8")
    missing = tmp_path / "missing.md"
    stderr_path = tmp_path / "stderr.txt"
    resolved = [
        arg.replace("{content}", str(content)).replace("{missing}", str(missing))
        for arg in args
    ]
    result = _tracking_issue_subprocess_stderr_redirected(
        resolved,
        tmp_path,
        stderr_path,
        extra_env={
            config.ENV_LARCH_QUIET_ACTIVE: "1",
            config.ENV_LARCH_QUIET_PID: str(os.getpid()),
        },
    )
    stderr = stderr_path.read_text(encoding="utf-8")
    assert result.returncode == returncode
    assert result.stdout == ""
    assert "FAILED=true" in stderr
    assert f"ERROR={expected}" in stderr


def test_upsert_summary_gh_failure_emits_stderr_under_inherited_quiet(
    tmp_path: Path,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("body", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text("#!/bin/sh\nprintf 'gh boom\\n' >&2\nexit 1\n", encoding="utf-8")
    fake_gh.chmod(0o755)
    stderr_path = tmp_path / "stderr.txt"
    result = _tracking_issue_subprocess_stderr_redirected(
        [
            "upsert-summary",
            "--issue",
            "1",
            "--marker",
            "<!-- larch:plan v1 runid=run1 -->",
            "--content-file",
            str(content),
            "--repo",
            "o/r",
        ],
        tmp_path,
        stderr_path,
        extra_env={
            "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            config.ENV_LARCH_QUIET_ACTIVE: "1",
            config.ENV_LARCH_QUIET_PID: str(os.getpid()),
        },
    )
    stderr = stderr_path.read_text(encoding="utf-8")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "FAILED=true" in stderr
    assert "ERROR=gh api comments fetch failed: gh boom" in stderr


def test_upsert_summary_redaction_failure_emits_stderr_under_inherited_quiet(
    tmp_path: Path,
) -> None:
    content = tmp_path / "summary.md"
    content.write_text("-----BEGIN PRIVATE KEY-----\nsecret\n", encoding="utf-8")
    stderr_path = tmp_path / "stderr.txt"
    result = _tracking_issue_subprocess_stderr_redirected(
        [
            "upsert-summary",
            "--issue",
            "1",
            "--marker",
            "<!-- larch:plan v1 runid=run1 -->",
            "--content-file",
            str(content),
            "--repo",
            "o/r",
        ],
        tmp_path,
        stderr_path,
        extra_env={
            config.ENV_LARCH_QUIET_ACTIVE: "1",
            config.ENV_LARCH_QUIET_PID: str(os.getpid()),
        },
    )
    stderr = stderr_path.read_text(encoding="utf-8")
    assert result.returncode == 3
    assert result.stdout == ""
    assert "FAILED=true" in stderr
    assert "ERROR=redaction: redaction failed for tracking-issue summary" in stderr


def test_cli_registry_tracking_issue_read_sentinel(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "parent-issue.md"
    path.write_text("ISSUE_NUMBER=5\nRUN_ID=run\nADOPTED=false\n", encoding="utf-8")
    rc = cli.main(["tracking-issue", "read", "--sentinel", str(path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISSUE_NUMBER=5" in out


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["tracking-issue", "create-issue", "--title", "t", "--body-file", "missing.md"], "body file not found"),
        (["tracking-issue", "rename", "--issue", "1", "--state", "bogus", "--repo", "o/r"], "invalid --state"),
        (["tracking-issue", "mark-false-positive", "--issue", "abc", "--repo", "o/r"], "invalid issue"),
    ],
)
def test_cli_registry_tracking_issue_write_verbs_validate_locally(
    argv: list[str],
    expected: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(tracking_issue, "proc", runner)
    monkeypatch.setattr(tracking_issue.logging_util, "quiet_init", _quiet_noop)
    rc = cli.main(argv)
    captured = capsys.readouterr()
    assert rc == 1
    assert expected in captured.out
    assert not runner.calls
