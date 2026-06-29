"""Tests for issue_wire.py parity surfaces."""

from __future__ import annotations

import os
import subprocess
import sys
import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable, Mapping, Sequence

import pytest

from larch.core import config
from larch.git import gh
from larch.issue import issue_wire
from larch.core import logging_util
from larch.core import retry
from larch.errors import ShipError
from larch.core.proc import CommandResult


def test_emit_untrusted_content_block_matches_file_block_redaction(tmp_path: Path) -> None:
    raw = "<tag> sk-" + "A" * 24 + " & text"
    file_path = tmp_path / "raw.txt"
    _ = file_path.write_text(raw, encoding="utf-8")
    assert issue_wire.emit_untrusted_content_block(tag="sample", text=raw) == issue_wire.emit_untrusted_file_block(tag="sample", path=file_path)
    out = issue_wire.emit_untrusted_content_block(tag="sample", text=raw)
    assert "&lt;tag&gt;" in out
    assert "&lt;REDACTED-TOKEN&gt;" in out


def test_untrusted_content_block_cli_reads_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert issue_wire.untrusted_content_block_main(["sample", "--text", "hello <world>"]) == 0
    assert "hello &lt;world&gt;" in capsys.readouterr().out


def test_parse_named_block_marker_isolated_and_whitespace_tolerant() -> None:
    body = """before
  <!--   larch:design-pause:start   -->  
pause
  <!--   larch:design-pause:end   -->
<!-- larch:plan:start -->
plan
<!-- larch:plan:end -->
after
"""
    assert issue_wire.parse_named_block(body=body, marker="plan") == ("plan\n", "")
    assert issue_wire.parse_named_block(body=body, marker="design-pause") == ("pause\n", "")
    assert issue_wire.parse_named_block(body=body, marker="other") == (None, "")


@pytest.mark.parametrize(
    ("body", "token"),
    [
        ("<!-- larch:plan:start -->\na\n<!-- larch:plan:end -->\n<!-- larch:plan:start -->\nb\n<!-- larch:plan:end -->\n", "multiple-start"),
        ("<!-- larch:plan:start -->\na\n<!-- larch:plan:end -->\n<!-- larch:plan:end -->\n", "multiple-end"),
        ("<!-- larch:plan:start -->\na\n", "start-without-end"),
        ("<!-- larch:plan:end -->\n", "end-without-start"),
        ("<!-- larch:plan:end -->\na\n<!-- larch:plan:start -->\n", "end-before-start"),
    ],
)
def test_parse_named_block_malformed_tokens(body: str, token: str) -> None:
    assert issue_wire.parse_named_block(body=body, marker="plan") == (None, token)
    assert issue_wire.strip_named_block(body=body, marker="plan") == ("", token)


def test_strip_named_block_preserves_unrelated_blocks() -> None:
    body = """intro
<!-- larch:design-pause:start -->
pause
<!-- larch:design-pause:end -->
<!-- larch:plan:start -->
plan
<!-- larch:plan:end -->
tail
"""
    stripped, malformed = issue_wire.strip_named_block(body=body, marker="plan")
    assert malformed == ""
    assert "larch:design-pause:start" in stripped
    assert "plan\n" not in stripped
    assert stripped.endswith("tail\n")


def test_compose_named_block_strips_trailing_lf() -> None:
    assert issue_wire.compose_named_block(marker="plan", inner="inner\n\n") == (
        "<!-- larch:plan:start -->\ninner\n<!-- larch:plan:end -->\n"
    )
    assert issue_wire.compose_named_block(marker="plan", inner="") == (
        "<!-- larch:plan:start -->\n<!-- larch:plan:end -->\n"
    )


def _empty_str_list() -> list[str]:
    return []


def _empty_call_list() -> list[list[str]]:
    return []


@dataclass
class IssueRunner:
    body: str
    edit_bodies: list[str] = field(default_factory=_empty_str_list)
    calls: list[list[str]] = field(default_factory=_empty_call_list)
    edit_failures: int = 0

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        args = list(argv)
        self.calls.append(args)
        if args[:4] == ["gh", "issue", "view", "9"]:
            return CommandResult(tuple(args), 0, '{"body": ' + __import__("json").dumps(self.body) + "}", "", 0.01)
        if args[:4] == ["gh", "issue", "edit", "9"]:
            body_file = args[args.index("--body-file") + 1]
            self.edit_bodies.append(Path(body_file).read_text(encoding="utf-8"))
            if self.edit_failures:
                self.edit_failures -= 1
                return CommandResult(tuple(args), 1, "", "Could not resolve host", 0.01)
            return CommandResult(tuple(args), 0, "", "", 0.01)
        if args[:3] == ["gh", "repo", "view"]:
            return CommandResult(tuple(args), 0, "owner/repo\n", "", 0.01)
        raise AssertionError(f"unexpected call: {args}")


def test_named_block_write_append_replace_delete_and_lf_normalization() -> None:
    runner = IssueRunner("hello\n\n")
    result = issue_wire.named_block_write(runner=runner, marker="plan", issue="9", repo="owner/repo", content="NEW\n", delete=False)
    assert result["mode"] == "appended"
    assert result["markers_present"] is False
    assert runner.edit_bodies[-1].startswith("hello\n\n<!-- larch:plan:start -->")

    runner = IssueRunner("before\n<!-- larch:plan:start -->\nOLD\n<!-- larch:plan:end -->\nafter\n")
    result = issue_wire.named_block_write(runner=runner, marker="plan", issue="9", repo="owner/repo", content="NEW\n", delete=False)
    assert result["mode"] == "replaced"
    assert "OLD" not in runner.edit_bodies[-1]
    assert "before\n<!-- larch:plan:start -->\nNEW\n<!-- larch:plan:end -->\nafter" in runner.edit_bodies[-1]

    runner = IssueRunner("body")
    result = issue_wire.named_block_write(runner=runner, marker="design-pause", issue="9", repo="owner/repo", content=None, delete=True)
    assert result["mode"] == "absent-noop"
    assert runner.edit_bodies == ["body\n"]


def test_named_block_write_malformed_skips_edit() -> None:
    runner = IssueRunner("<!-- larch:plan:start -->\nno end")
    result = issue_wire.named_block_write(runner=runner, marker="plan", issue="9", repo="owner/repo", content="x", delete=False)
    assert result == {"malformed": "start-without-end"}
    assert not any(call[:3] == ["gh", "issue", "edit"] for call in runner.calls)


def test_issue_body_redaction_and_no_second_redaction() -> None:
    token = "sk-" + "A" * 24
    runner = IssueRunner("")
    result = issue_wire.named_block_write(runner=runner, marker="plan", issue="9", repo="owner/repo", content=token, delete=False)
    assert result["mode"] == "appended"
    assert token not in runner.edit_bodies[-1]
    assert "<REDACTED-TOKEN>" in runner.edit_bodies[-1]


def test_plan_block_read_cli_contracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = IssueRunner("<!-- larch:plan:start -->\ninner\n<!-- larch:plan:end -->\n")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)
    out = tmp_path / "plan.md"
    assert issue_wire.plan_block_read_main(["--issue", "9", "--output", str(out), "--repo", "owner/repo"]) == 0
    stdout = capsys.readouterr().out
    assert "BLOCK_PRESENT=true" in stdout
    assert f"OUTPUT={out}" in stdout
    assert out.read_text(encoding="utf-8") == "inner\n"

    runner.body = "<!-- larch:plan:start -->\n"
    assert issue_wire.plan_block_read_main(["--issue", "9", "--output", str(out), "--repo", "owner/repo"]) == 1
    assert capsys.readouterr().out == "MALFORMED=start-without-end\n"
    assert out.read_text(encoding="utf-8") == ""


def test_plan_block_write_cli_invalid_issue_before_gh(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = IssueRunner("")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)
    assert issue_wire.plan_block_write_main(["--issue", "0", "--content-file", "x", "--repo", "owner/repo"]) == 1
    assert "--issue must be a positive integer" in capsys.readouterr().err
    assert not runner.calls


def test_write_cli_no_repo_resolves_with_gh_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = tmp_path / "content.md"
    _ = content.write_text("body", encoding="utf-8")
    runner = IssueRunner("")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)
    assert issue_wire.named_block_write_main(["--marker", "plan", "--issue", "9", "--content-file", str(content)]) == 0
    assert runner.calls[0][:3] == ["gh", "repo", "view"]
    assert "WRITTEN=true" in capsys.readouterr().out


class FailingRepoRunner(IssueRunner):
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        args = list(argv)
        self.calls.append(args)
        if args[:3] == ["gh", "repo", "view"]:
            return CommandResult(tuple(args), 1, "", "no repo", 0.01)
        raise AssertionError(f"unexpected call: {args}")


class FailingIssueViewRunner(IssueRunner):
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        args = list(argv)
        self.calls.append(args)
        if args[:4] == ["gh", "issue", "view", "9"]:
            return CommandResult(tuple(args), 2, "", "GraphQL: could not resolve to an Issue", 0.01)
        raise AssertionError(f"unexpected call: {args}")


def test_write_cli_no_repo_failure_has_no_origin_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    content = tmp_path / "content.md"
    _ = content.write_text("body", encoding="utf-8")
    runner = FailingRepoRunner("")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)
    assert issue_wire.named_block_write_main(["--marker", "plan", "--issue", "9", "--content-file", str(content)]) == 2
    assert capsys.readouterr().out == "FAILED=true\nERROR=could not determine repo\n"
    assert all(call[:2] != ["git", "remote"] for call in runner.calls)


def test_plan_block_read_gh_failure_does_not_emit_invalid_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = FailingIssueViewRunner("")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)
    out = tmp_path / "plan.md"
    assert issue_wire.plan_block_read_main(["--issue", "9", "--output", str(out), "--repo", "owner/repo"]) == 2
    stdout = capsys.readouterr().out
    assert "FAILED=true" in stdout
    assert "ERROR=invalid-repo" not in stdout
    assert out.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize(
    ("entrypoint", "argv_prefix"),
    [
        (issue_wire.named_block_write_main, ["--marker", "plan"]),
        (issue_wire.plan_block_write_main, []),
    ],
)
def test_write_cli_redaction_failure_exits_3(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    entrypoint: Callable[[list[str]], int],
    argv_prefix: list[str],
) -> None:
    content = tmp_path / "content.md"
    _ = content.write_text("body", encoding="utf-8")
    runner = IssueRunner("")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)

    def fail_redaction(_text: str) -> str:
        raise ShipError("redaction:fixture")

    _ = monkeypatch.setattr(issue_wire.redact, "redact_secrets_only", fail_redaction)
    rc = entrypoint([*argv_prefix, "--issue", "9", "--content-file", str(content), "--repo", "owner/repo"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "FAILED=true" in out
    assert "ERROR=redaction:" in out
    assert not any(call[:3] == ["gh", "issue", "edit"] for call in runner.calls)


def _capture_contract_from_self_quiet(call: Callable[[], int], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
    saved_fd3: int | None = None
    saved_fd4: int | None = None
    with contextlib.suppress(OSError):
        saved_fd3 = os.dup(3)
    with contextlib.suppress(OSError):
        saved_fd4 = os.dup(4)
    try:
        _ = os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = call()
        _ = os.dup2(saved_stdout, 1)
        _ = os.dup2(saved_stderr, 2)
        contract = os.read(read_fd, 4096).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        os.close(saved_stderr)
        if saved_fd3 is not None:
            _ = os.dup2(saved_fd3, 3)
            os.close(saved_fd3)
        else:
            with contextlib.suppress(OSError):
                os.close(3)
        if saved_fd4 is not None:
            _ = os.dup2(saved_fd4, 4)
            os.close(saved_fd4)
        else:
            with contextlib.suppress(OSError):
                os.close(4)
        logging_util.reset_quiet_state()
    return rc, contract


def test_plan_block_read_emits_kv_on_fd3_under_quiet_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = IssueRunner("<!-- larch:plan:start -->\ninner\n<!-- larch:plan:end -->\n")
    _ = monkeypatch.setattr(issue_wire, "proc", runner)
    out = tmp_path / "plan.md"
    rc, contract = _capture_contract_from_self_quiet(
        lambda: issue_wire.plan_block_read_main(["--issue", "9", "--output", str(out), "--repo", "owner/repo"]),
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "BLOCK_PRESENT=true\n" in contract
    assert f"OUTPUT={out}\n" in contract


def test_plan_block_strip_body_malformed_emits_kv_on_fd3_under_quiet_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    body = tmp_path / "body.md"
    out = tmp_path / "out.md"
    _ = body.write_text("<!-- larch:plan:start -->\n", encoding="utf-8")
    rc, contract = _capture_contract_from_self_quiet(
        lambda: issue_wire.plan_block_strip_body_main(["--file", str(body), "--output", str(out)]),
        tmp_path,
        monkeypatch,
    )
    assert rc == 1
    assert contract == "MALFORMED=start-without-end\n"
    assert out.read_text(encoding="utf-8") == ""


def test_plan_block_strip_body_quiet_subprocess_routes_kv_to_stdout(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    out = tmp_path / "out.md"
    _ = body.write_text("<!-- larch:plan:start -->\n", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(tmp_path)
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    result = subprocess.run(
        [sys.executable, "python/cli.py", "plan-block", "strip-body", "--file", str(body), "--output", str(out)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 1
    assert result.stdout == "MALFORMED=start-without-end\n"


def test_plan_block_strip_body_inherited_quiet_diagnostic_uses_stderr(tmp_path: Path) -> None:
    side_fd4 = tmp_path / "fd4.txt"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env[config.ENV_LARCH_QUIET_ACTIVE] = "1"
    env[config.ENV_LARCH_QUIET_PID] = "999999"
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    _ = env.pop(config.ENV_LARCH_QUIET_LOG_FILE, None)
    saved_fd4: int | None = None
    with contextlib.suppress(OSError):
        saved_fd4 = os.dup(4)
    fd4 = os.open(side_fd4, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        if fd4 != 4:
            _ = os.dup2(fd4, 4)
            os.close(fd4)
        result = subprocess.run(
            [
                sys.executable,
                "python/cli.py",
                "plan-block",
                "strip-body",
                "--file",
                str(tmp_path / "missing.md"),
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
            env=env,
            pass_fds=(4,),
        )
    finally:
        if saved_fd4 is not None:
            _ = os.dup2(saved_fd4, 4)
            os.close(saved_fd4)
        else:
            with contextlib.suppress(OSError):
                os.close(4)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "plan-block-strip-body.sh:" in result.stderr
    assert side_fd4.read_text(encoding="utf-8") == ""


def test_plan_block_read_quiet_subprocess_routes_usage_to_stderr(tmp_path: Path) -> None:
    out = tmp_path / "plan.md"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env[config.ENV_IMPLEMENT_TMPDIR] = str(tmp_path)
    _ = env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    result = subprocess.run(
        [sys.executable, "python/cli.py", "plan-block", "read", "--issue", "0", "--output", str(out)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "plan-block-read.sh: --issue must be a positive integer" in result.stderr


def test_plan_block_strip_body_file_stdin_stdout_and_malformed(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    body = tmp_path / "body.md"
    _ = body.write_text("Intro\n<!-- larch:plan:start -->\nin\n<!-- larch:plan:end -->\nTail\n", encoding="utf-8")
    out = tmp_path / "out.md"
    assert issue_wire.plan_block_strip_body_main(["--file", str(body), "--output", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "Intro\nTail\n"

    _ = monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("plain\n"))
    assert issue_wire.plan_block_strip_body_main([]) == 0
    assert capsys.readouterr().out == "plain\n"

    _ = body.write_text("<!-- larch:plan:start -->\n", encoding="utf-8")
    assert issue_wire.plan_block_strip_body_main(["--file", str(body), "--output", str(out)]) == 1
    assert capsys.readouterr().out == "MALFORMED=start-without-end\n"
    assert out.read_text(encoding="utf-8") == ""


def test_extract_scope_paths_and_cli_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan = """## Plan
### UPDATED: `outside.txt`
## Files to modify/create
### MAY_UPDATE: `docs/optional.md`
### MAY_UPDATE: `a/b.py`
### UPDATED: `a/b.py`, `c/d.md`
### REWRITTEN: skills/design/scripts/x.sh (legacy)
## Acceptance
"""
    assert issue_wire.extract_scope_paths(plan_text=plan) == ["docs/optional.md", "a/b.py", "c/d.md", "skills/design/scripts/x.sh"]
    assert issue_wire.extract_scope_paths(plan_text=plan, include_optional=False) == ["a/b.py", "c/d.md", "skills/design/scripts/x.sh"]
    empty = tmp_path / "empty.md"
    _ = empty.write_text("## Files to modify/create\n\n## Acceptance\n", encoding="utf-8")
    assert issue_wire.extract_scope_paths(plan_text=empty.read_text(encoding="utf-8")) == ["skills/design/SKILL.md"]
    assert issue_wire.extract_scope_paths(plan_text=empty.read_text(encoding="utf-8"), use_fallback=False) == []
    scopeless = "## Plan\n### UPDATED: `docs/expected.md`\n## Acceptance\n"
    assert issue_wire.extract_scope_paths(plan_text=scopeless, use_fallback=False) == []
    optional = tmp_path / "optional.md"
    _ = optional.write_text(plan, encoding="utf-8")
    assert issue_wire.plan_scope_paths_main(["--plan-file", str(optional)]) == 0
    assert capsys.readouterr().out.splitlines() == ["docs/optional.md", "a/b.py", "c/d.md", "skills/design/scripts/x.sh"]
    assert issue_wire.plan_scope_paths_main(["--plan-file", str(empty), "-z"]) == 0
    assert capsys.readouterr().out == "skills/design/SKILL.md\0"
    assert issue_wire.plan_scope_paths_main(["--plan-file", str(tmp_path / "missing.md")]) == 2
    assert "plan file not found" in capsys.readouterr().err


def test_title_eligibility_and_insert_signal_marker() -> None:
    assert issue_wire.title_lifecycle_reject_marker("  [implementing] x") == "[IMPLEMENTING]"
    assert issue_wire.title_lifecycle_reject_marker("[STALLED] x") is None
    assert issue_wire.title_has_archival_report_prefix("  [Analysis Report] x")
    assert not issue_wire.title_has_archival_report_prefix("[Run Logs Audit Report 2026] x")
    assert issue_wire.title_starts_with_brainstorm(" Brainstorm-mode")
    assert not issue_wire.title_starts_with_brainstorm("Brainstorming")
    assert issue_wire.insert_signal_marker(title="[DESIGNED] My feature", marker="FALSE-POSITIVE") == "[DESIGNED] [FALSE-POSITIVE] My feature"
    assert issue_wire.insert_signal_marker(title="[DESIGNED] [FALSE-POSITIVE] My feature", marker="FALSE-POSITIVE") == "[DESIGNED] [FALSE-POSITIVE] My feature"


def test_title_cli_leading_hyphen_subprocess() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    result = subprocess.run(
        [sys.executable, "python/cli.py", "issue", "title-eligibility", "--title", "-starts-with-hyphen"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "LIFECYCLE_REJECT=false" in result.stdout

    result_eq = subprocess.run(
        [sys.executable, "python/cli.py", "issue", "insert-signal-marker", "--title=-starts-with-hyphen", "--marker", "X"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result_eq.returncode == 0
    assert result_eq.stdout == "[X] -starts-with-hyphen"


def test_archival_jq_filter_matches_legacy_literal() -> None:
    expected = 'select((.title // "" | ascii_downcase | sub("^[[:space:]]+"; "")) as $t | (($t | startswith("research ")) or ($t | startswith("[research] ")) or ($t | startswith("investigate ")) or ($t | startswith("[investigate] ")) or ($t | test("^\\[.*report\\] "))) | not)'
    assert expected == issue_wire.ARCHIVAL_JQ_FILTER


def test_untrusted_helpers(tmp_path: Path) -> None:
    token = "sk-" + "B" * 24
    assert issue_wire.xml_escape_attr("a&b\"<c>'") == "a&amp;b&quot;&lt;c&gt;'"
    redacted = issue_wire.redact_untrusted_stream(f"<{token}&>")
    assert "&lt;" in redacted
    assert "&amp;" in redacted
    assert token not in redacted
    file = tmp_path / "payload.txt"
    _ = file.write_text("<x>", encoding="utf-8")
    assert issue_wire.emit_untrusted_file_block(tag="tag", path=file) == '<tag encoding="literal-redacted">\n&lt;x&gt;\n\n</tag>\n\n'


def test_p3119_lint_constructed_tokens(tmp_path: Path) -> None:
    clean = tmp_path / "clean.md"
    _ = clean.write_text("ok", encoding="utf-8")
    assert issue_wire.lint_p3119_fence_absence(path=clean, label="clean") == []
    bad = tmp_path / "bad.md"
    _ = bad.write_text("\n".join(issue_wire.P3119_TOKENS), encoding="utf-8")
    violations = issue_wire.lint_p3119_fence_absence(path=bad, label="bad")
    assert len(violations) == len(issue_wire.P3119_TOKENS)


def test_gh_issue_view_body_and_edit_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = IssueRunner("body", edit_failures=2)
    def retry_no_sleep(
        fn: Callable[[], tuple[CommandResult, int, str]],
    ) -> retry.RetryResult[CommandResult]:
        return retry.with_transient_retry(fn, sleeper=lambda _seconds: None)

    _ = monkeypatch.setattr(gh, "with_transient_retry", retry_no_sleep)
    body = gh.issue_view_body(runner, "9", repo="owner/repo")
    assert body == "body"
    result = gh.issue_edit_body_with_retry(runner, "9", "redacted", repo="owner/repo")
    assert result.returncode == 0
    edit_calls = [call for call in runner.calls if call[:3] == ["gh", "issue", "edit"]]
    assert len(edit_calls) == 3
    assert runner.edit_bodies[-1] == "redacted"
