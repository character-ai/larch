# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for issue_query.py."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
import pytest

from larch.issue import issue_query
from larch.errors import ShipError
from larch.core.proc import CommandResult
from test_support import RecordingRunner


def _result(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("gh",), rc, stdout, stderr, 0.01)


def test_issue_state_construction() -> None:
    assert issue_query.IssueState("OPEN", "https://github.com/o/r/issues/1", is_pr=False).state == "OPEN"


@pytest.mark.parametrize(
    ("url", "is_pr"),
    [("https://github.com/o/r/issues/1", False), ("https://github.com/o/r/pull/1", True)],
)
def test_issue_state(url: str, is_pr: bool) -> None:
    runner = RecordingRunner(responses=[_result(stdout=json.dumps({"state": "OPEN", "url": url}))])
    assert issue_query.issue_state(runner, "1", repo="o/r") == issue_query.IssueState("OPEN", url, is_pr)


@pytest.mark.parametrize("result", [_result(rc=1, stderr="bad"), _result(stdout="not json")])
def test_issue_state_failures(result: CommandResult) -> None:
    runner = RecordingRunner(responses=[result])
    with pytest.raises(ShipError):
        issue_query.issue_state(runner, "1", repo="o/r")


def test_issue_info_state_url_and_failures() -> None:
    runner = RecordingRunner(
        responses=[
            _result(stdout=json.dumps({"state": "OPEN"})),
            _result(stdout=json.dumps({"url": "u"})),
            _result(rc=1),
        ]
    )
    assert issue_query.issue_info(runner, "1", "state", repo="o/r") == "OPEN"
    assert issue_query.issue_info(runner, "1", "url", repo="o/r") == "u"
    assert issue_query.issue_info(runner, "1", "state", repo="o/r") == ""
    assert issue_query.issue_info(runner, "1", "bad", repo="o/r") == ""


def test_issue_context_writes_files(tmp_path: Path) -> None:
    runner = RecordingRunner(responses=[_result(stdout=json.dumps({"title": "T", "body": "B"}))])
    title, body = issue_query.issue_context(runner, "1", repo="o/r", tmpdir=tmp_path / "missing")
    assert title.read_text(encoding="utf-8") == "T"
    assert body.read_text(encoding="utf-8") == "B"
    assert title.name == "upstream-issue-title.txt"
    assert body.name == "upstream-issue-body.txt"
    assert not title.with_suffix(".txt.tmp").exists()


def test_issue_context_failures(tmp_path: Path) -> None:
    with pytest.raises(ShipError):
        issue_query.issue_context(RecordingRunner(responses=[_result(rc=1)]), "1", repo="o/r", tmpdir=tmp_path)
    with pytest.raises(ShipError):
        issue_query.issue_context(RecordingRunner(responses=[_result(stdout="not json")]), "1", repo="o/r", tmpdir=tmp_path)


def test_issue_state_cli_emit_kv(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(issue_query.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    monkeypatch.setattr(
        issue_query,
        "issue_state",
        lambda *_args, **_kwargs: issue_query.IssueState("OPEN", "https://github.com/o/r/pull/2", is_pr=True),
    )
    assert issue_query.issue_state_main(["--issue", "2", "--repo", "o/r"]) == 0
    assert emitted == [("STATE", "OPEN"), ("URL", "https://github.com/o/r/pull/2"), ("IS_PR", "true")]


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        ([], "--issue is required"),
        (["--issue"], "--issue requires a value"),
        (["--issue", "abc"], "--issue must be numeric"),
        (["--issue", "--repo", "o/r"], "--issue requires a value"),
        (["--issue", "12", "--repo"], "--repo requires a value"),
        (["--issue", "12", "--repo", "--flag"], "--repo requires a value"),
        (["--wat"], "unknown flag: --wat"),
    ],
)
def test_issue_state_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    error: str,
) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(issue_query.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    assert issue_query.issue_state_main(argv) == 1
    assert emitted == [("FAILED", "true"), ("ERROR", error)]


def test_issue_info_cli_emit_kv(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(issue_query.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    monkeypatch.setattr(issue_query, "issue_info", lambda *_args, **_kwargs: "OPEN")
    assert issue_query.issue_info_main(["--issue", "1", "--field", "state", "--repo", "o/r"]) == 0
    assert emitted == [("VALUE", "OPEN")]


@pytest.mark.parametrize("argv", [["--issue"], ["--field"], ["--repo"]])
def test_issue_info_cli_missing_values(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    assert issue_query.issue_info_main(argv) == 1


@pytest.mark.parametrize("argv", [[], ["--issue", "1"], ["--field", "state"], ["--issue", "1", "--field", "bad"], ["--wat"]])
def test_issue_info_cli_empty_value(argv: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(issue_query.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    assert issue_query.issue_info_main(argv) == 0
    assert emitted == [("VALUE", "")]


def test_issue_context_cli_emit_kv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(issue_query.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    monkeypatch.setattr(issue_query, "issue_context", lambda *_args, **_kwargs: (tmp_path / "t", tmp_path / "b"))
    assert issue_query.issue_context_main(["--issue", "1", "--repo", "o/r", "--tmpdir", str(tmp_path)]) == 0
    assert emitted == [("TITLE_FILE", str(tmp_path / "t")), ("BODY_FILE", str(tmp_path / "b"))]


def test_issue_context_cli_runtime_shiperror_emits_failure_kv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[tuple[str, str]] = []

    def raise_context(*_args: object, **_kwargs: object) -> tuple[Path, Path]:
        raise ShipError("boom")

    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(issue_query.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    monkeypatch.setattr(issue_query, "issue_context", raise_context)
    assert issue_query.issue_context_main(["--issue", "1", "--repo", "o/r", "--tmpdir", str(tmp_path)]) == 1
    assert emitted == [("FAILED", "true"), ("ERROR", "boom")]


@pytest.mark.parametrize(
    ("argv", "rc"),
    [
        ([], 2),
        (["--issue", "0", "--repo", "o/r", "--tmpdir", "/tmp/x"], 2),
        (["--issue", "1", "--repo", "bad", "--tmpdir", "/tmp/x"], 2),
        (["--unknown"], 2),
        (["--issue"], 1),
        (["--repo"], 1),
        (["--tmpdir"], 1),
    ],
)
def test_issue_context_cli_validation(argv: list[str], rc: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(issue_query.logging_util, "quiet_init", lambda **_: None)
    assert issue_query.issue_context_main(argv) == rc


def _write_gh_stub(tmp_path: Path, body: str) -> dict[str, str]:
    stub = tmp_path / "gh"
    stub.write_text(body, encoding="utf-8")
    stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    return env


def _run_cli(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "python/cli.py", *args],
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue_context_cli_help_and_usage_visible_under_quiet(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_path)
    usage = "Usage: get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH\n"
    help_result = _run_cli(["issue", "context", "--help"], env)
    assert help_result.returncode == 0
    assert help_result.stdout == usage
    assert help_result.stderr == ""
    usage_result = _run_cli(["issue", "context", "--unknown"], env)
    assert usage_result.returncode == 2
    assert usage_result.stdout == ""
    assert usage_result.stderr == usage


def test_issue_state_cli_subprocess_repo_paths(tmp_path: Path) -> None:
    log = tmp_path / "argv.log"
    env = _write_gh_stub(
        tmp_path,
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {log}\n"
        "if [[ $1 == repo ]]; then echo resolved/repo; exit 0; fi\n"
        "if [[ $1 == issue ]]; then printf '{\"state\":\"OPEN\",\"url\":\"https://github.com/o/r/issues/1\"}'; exit 0; fi\n"
        "exit 99\n",
    )
    explicit = _run_cli(["issue", "state", "--issue", "1", "--repo", "o/r"], env)
    assert explicit.returncode == 0
    assert "IS_PR=false" in explicit.stdout
    omitted = _run_cli(["issue", "state", "--issue", "1"], env)
    assert omitted.returncode == 0
    assert "--repo resolved/repo" in log.read_text(encoding="utf-8")


def test_issue_state_empty_resolution_omits_repo(tmp_path: Path) -> None:
    log = tmp_path / "argv.log"
    env = _write_gh_stub(
        tmp_path,
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {log}\n"
        "if [[ $1 == repo ]]; then exit 1; fi\n"
        "if [[ $1 == issue ]]; then printf '{\"state\":\"OPEN\",\"url\":\"https://github.com/o/r/issues/1\"}'; exit 0; fi\n"
        "exit 99\n",
    )
    git_stub = tmp_path / "git"
    git_stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    git_stub.chmod(0o755)
    result = _run_cli(["issue", "state", "--issue", "1"], env)
    assert result.returncode == 0
    assert "STATE=OPEN" in result.stdout
    assert "--repo" not in log.read_text(encoding="utf-8").splitlines()[-1]


def test_issue_info_empty_resolution_omits_repo(tmp_path: Path) -> None:
    log = tmp_path / "argv.log"
    env = _write_gh_stub(
        tmp_path,
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {log}\n"
        "if [[ $1 == repo ]]; then exit 1; fi\n"
        "if [[ $1 == issue ]]; then printf '{\"state\":\"OPEN\"}'; exit 0; fi\n"
        "exit 99\n",
    )
    git_stub = tmp_path / "git"
    git_stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    git_stub.chmod(0o755)
    result = _run_cli(["issue", "info", "--issue", "1", "--field", "state"], env)
    assert result.returncode == 0
    assert "VALUE=OPEN" in result.stdout
    assert "--repo" not in log.read_text(encoding="utf-8").splitlines()[-1]
