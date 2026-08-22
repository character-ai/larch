"""Tests for the one-call complete-umbrella Step 0 bootstrap."""

from __future__ import annotations

import stat
from collections.abc import Mapping
from pathlib import Path

import pytest

from larch import complete_umbrella
from larch.core.proc import CommandResult
from tests.support.foundation import RecordingRunner


def _result(stdout: str = "", *, returncode: int = 0, stderr: str = "") -> CommandResult:
    return CommandResult((), returncode, stdout, stderr, 0.0)


def _lifecycle() -> str:
    return (
        "RUN_ID=run-8651\n"
        "SKILL=complete-umbrella\n"
        "LOG_ROOT=/tmp/larch-log\n"
        "RUN_DIR=/tmp/larch-run\n"
        "CONTEXT_FILE=/tmp/larch-context.json\n"
        "RUN_LOG_STORAGE=disabled\n"
        "RUN_LOG_STORAGE_REASON=config-file-missing\n"
        "STORAGE_BASE_URI=\n"
        "CLIENT_REPO=larch\n"
        "TOOL_REPO_URI=\n"
        "RUN_LOGS_URI=\n"
        "STORAGE_PREFLIGHT=skipped-disabled\n"
        "PREFLIGHT_OK=true\n"
        "LIFECYCLE_STARTED=true\n"
    )


def _environment(repo: Path, home: Path) -> dict[str, str]:
    return {
        "CLAUDE_PROJECT_DIR": str(repo),
        "HOME": str(home),
        "LARCH_CLAUDE_PID": "4242",
    }


def _fresh_responses(session: Path, pointer: Path) -> list[CommandResult]:
    return [
        _result(_lifecycle()),
        _result("character-ai/larch\n"),
        _result("RESUME_FOUND=false\n"),
        _result(f"SESSION_TMPDIR={session}\nSESSION_ID=test-session\n"),
        _result(
            "UMBRELLA_STARTED=true\n"
            "UMBRELLA_ISSUE=8651\n"
            f"COMPLETE_UMBRELLA_TMPDIR={session}\n"
            f"COMPLETE_UMBRELLA_POINTER={pointer}\n"
        ),
        _result("CLAUDE_MODEL=claude-opus-4-8\n"),
    ]


def _fresh_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Mapping[str, str]]:
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    home: Path = tmp_path / "home"
    home.mkdir()
    session: Path = tmp_path / "session"
    session.mkdir()
    pointer: Path = home / ".cache" / "larch" / "sessions" / "pointer.env"
    pointer.parent.mkdir(parents=True)
    _ = pointer.write_text("pointer\n", encoding="utf-8")
    return repo, home, session, pointer, _environment(repo, home)


def test_fresh_bootstrap_emits_one_validated_block_and_internal_copies(
    tmp_path: Path,
) -> None:
    _repo, _home, session, pointer, environ = _fresh_fixture(tmp_path)
    plugin_root: Path = tmp_path / "plugin"
    plugin_root.mkdir()
    runner = RecordingRunner(
        responses=_fresh_responses(session, pointer),
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="/tmp/parent-context.json",
        environ=environ,
        plugin_root=plugin_root,
        fallback_pid=999,
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.count("BOOTSTRAP_OK=true\n") == 1
    for row in (
        "REPO=character-ai/larch\n",
        "UMBRELLA_STARTED=true\n",
        f"SESSION_TMPDIR={session}\n",
        f"COMPLETE_UMBRELLA_TMPDIR={session}\n",
        "RESUME_ACTION=reselect\n",
        "CLAUDE_MODEL=claude-opus-4-8\n",
    ):
        assert row in result.stdout
    assert (session / "complete-umbrella-bootstrap.env").read_text(
        encoding="utf-8"
    ) == result.stdout
    assert (session / "model.env").read_text(encoding="utf-8") == (
        "CLAUDE_MODEL=claude-opus-4-8\n"
    )
    sentinel_rows: list[str] = [
        line for line in result.stdout.splitlines() if line.startswith("COMPLETE_UMBRELLA_WRITE_SENTINEL=")
    ]
    assert len(sentinel_rows) == 1
    sentinel: Path = Path(sentinel_rows[0].split("=", 1)[1])
    assert sentinel.is_file()
    assert stat.S_IMODE(sentinel.stat().st_mode) == 0o600

    commands: list[list[str]] = runner.calls
    assert commands[0][1:3] == ["run-log", "lifecycle-start"]
    assert commands[0][-2:] == ["--lifecycle-parent-context", "/tmp/parent-context.json"]
    assert commands[1][1:] == ["gh", "resolve-repo"]
    assert commands[2][1:3] == ["complete-umbrella", "resume"]
    assert commands[3][1:3] == ["session", "setup"]
    assert commands[4][1:3] == ["complete-umbrella", "start"]
    assert commands[5][1:] == ["agent", "read-claude-model"]


def test_resume_reuses_the_existing_tmpdir_and_pinned_model(tmp_path: Path) -> None:
    _repo, _home, session, pointer, environ = _fresh_fixture(tmp_path)
    _ = (session / "model.env").write_text(
        "CLAUDE_MODEL=claude-sonnet-4-6\n", encoding="utf-8"
    )
    runner = RecordingRunner(
        responses=[
            _result(_lifecycle()),
            _result("character-ai/larch\n"),
            _result(
                "RESUME_FOUND=true\n"
                "RESUME_ACTION=wait\n"
                f"COMPLETE_UMBRELLA_TMPDIR={session}\n"
                f"COMPLETE_UMBRELLA_POINTER={pointer}\n"
                "BGJOB_STEP=complete-umbrella-leaves\n"
                "CURRENT_LEAF=8653\n"
                "CURRENT_STEP=launch\n"
                "TRANSIENT_ATTEMPT_COUNT=2\n"
            ),
        ],
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 0
    assert "RESUME_ACTION=wait\n" in result.stdout
    assert "CLAUDE_MODEL=claude-sonnet-4-6\n" in result.stdout
    assert len(runner.calls) == 3


def test_terminal_resume_skips_model_resolution(tmp_path: Path) -> None:
    _repo, _home, session, pointer, environ = _fresh_fixture(tmp_path)
    runner = RecordingRunner(
        responses=[
            _result(_lifecycle()),
            _result("character-ai/larch\n"),
            _result(
                "RESUME_FOUND=true\n"
                "RESUME_ACTION=needs-design\n"
                f"COMPLETE_UMBRELLA_TMPDIR={session}\n"
                f"COMPLETE_UMBRELLA_POINTER={pointer}\n"
                "BGJOB_STEP=complete-umbrella-leaves\n"
                "CURRENT_LEAF=8653\n"
                "CURRENT_STEP=failed\n"
                "TRANSIENT_ATTEMPT_COUNT=0\n"
                "NEXT_ACTION=needs-design\n"
                "FAILED_STEP=run-child\n"
                "FAILED_LEAF=8653\n"
                "FAILURE_REASON=plan is malformed\n"
            ),
        ],
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 0
    assert "CLAUDE_MODEL=\n" in result.stdout
    assert "NEXT_ACTION=needs-design\n" in result.stdout
    assert len(runner.calls) == 3


@pytest.mark.parametrize(
    ("failed_index", "expected_stage"),
    [
        (0, "lifecycle-start"),
        (1, "repository-resolve"),
        (2, "resume"),
        (3, "session-setup"),
        (4, "start"),
        (5, "model-resolve"),
    ],
)
def test_every_command_failure_names_its_stage(
    tmp_path: Path,
    failed_index: int,
    expected_stage: str,
) -> None:
    _repo, _home, session, pointer, environ = _fresh_fixture(tmp_path)
    responses: list[CommandResult] = _fresh_responses(session, pointer)
    responses[failed_index] = _result(returncode=1, stderr="backend unavailable\n")
    runner = RecordingRunner(responses=responses, strict=True)

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 1
    assert f"BOOTSTRAP_STAGE={expected_stage}\n" in result.stdout
    assert f"failed at stage={expected_stage}" in result.stderr
    assert "BOOTSTRAP_OK=false\n" in result.stdout
    if failed_index > 0:
        assert "LIFECYCLE_STARTED=true\n" in result.stdout
    if expected_stage == "start":
        assert f"SESSION_TMPDIR={session}\n" in result.stdout
        assert f"COMPLETE_UMBRELLA_TMPDIR={session}\n" in result.stdout


def test_stage_stdout_rejects_non_kv_noise(tmp_path: Path) -> None:
    repo, home, _session, _pointer, environ = _fresh_fixture(tmp_path)
    runner = RecordingRunner(
        responses=[_result(_lifecycle() + "unexpected prose\n")],
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert repo.is_dir()
    assert home.is_dir()
    assert result.exit_code == 1
    assert "BOOTSTRAP_STAGE=lifecycle-start\n" in result.stdout
    assert "BOOTSTRAP_ERROR=malformed non-KV stdout\n" in result.stdout


def test_repository_root_rejects_wire_line_breaks(tmp_path: Path) -> None:
    repo: Path = tmp_path / "repo\nFORGED=true"
    repo.mkdir()
    home: Path = tmp_path / "home"
    home.mkdir()
    runner = RecordingRunner(strict=True)

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=_environment(repo, home),
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 1
    assert "BOOTSTRAP_STAGE=repository-root\n" in result.stdout
    assert "\nFORGED=true\n" not in result.stdout
    assert runner.calls == []


def test_oversized_owner_pid_fails_at_its_validation_stage(tmp_path: Path) -> None:
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    home: Path = tmp_path / "home"
    home.mkdir()
    environ: dict[str, str] = _environment(repo, home)
    environ["LARCH_CLAUDE_PID"] = "9" * 5_000
    runner = RecordingRunner(strict=True)

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 1
    assert "BOOTSTRAP_STAGE=owner-pid\n" in result.stdout
    assert "BOOTSTRAP_ERROR=invalid CLAUDE_PID\n" in result.stdout
    assert runner.calls == []


def test_failed_session_setup_preserves_its_published_tmpdir(tmp_path: Path) -> None:
    _repo, _home, session, _pointer, environ = _fresh_fixture(tmp_path)
    runner = RecordingRunner(
        responses=[
            _result(_lifecycle()),
            _result("character-ai/larch\n"),
            _result("RESUME_FOUND=false\n"),
            _result(
                f"SESSION_TMPDIR={session}\nSESSION_ID=test-session\n",
                returncode=1,
                stderr="session environment write failed\n",
            ),
        ],
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 1
    assert "BOOTSTRAP_STAGE=session-setup\n" in result.stdout
    assert f"SESSION_TMPDIR={session}\n" in result.stdout
    assert f"COMPLETE_UMBRELLA_TMPDIR={session}\n" in result.stdout
    assert (session / "complete-umbrella-bootstrap.env").read_text(
        encoding="utf-8"
    ) == result.stdout


def test_write_hook_failure_is_named_and_keeps_the_session(tmp_path: Path) -> None:
    _repo, _home, session, pointer, environ = _fresh_fixture(tmp_path)
    isolated: dict[str, str] = dict(environ)
    _ = isolated.pop("HOME")
    runner = RecordingRunner(
        responses=_fresh_responses(session, pointer)[:-1],
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=isolated,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 1
    assert "BOOTSTRAP_STAGE=write-hook\n" in result.stdout
    assert session.is_dir()
    assert (session / "complete-umbrella-bootstrap.env").is_file()


def test_invalid_existing_model_fails_closed_without_resolving_again(tmp_path: Path) -> None:
    _repo, _home, session, pointer, environ = _fresh_fixture(tmp_path)
    _ = (session / "model.env").write_text(
        "CLAUDE_MODEL=unknown\n", encoding="utf-8"
    )
    runner = RecordingRunner(
        responses=[
            _result(_lifecycle()),
            _result("character-ai/larch\n"),
            _result(
                "RESUME_FOUND=true\n"
                "RESUME_ACTION=reselect\n"
                f"COMPLETE_UMBRELLA_TMPDIR={session}\n"
                f"COMPLETE_UMBRELLA_POINTER={pointer}\n"
                "BGJOB_STEP=complete-umbrella-leaves\n"
                "CURRENT_LEAF=0\n"
                "CURRENT_STEP=select\n"
                "TRANSIENT_ATTEMPT_COUNT=0\n"
            ),
        ],
        strict=True,
    )

    result: complete_umbrella.BootstrapResult = complete_umbrella.bootstrap(
        runner,
        issue=8651,
        operator_invoked=True,
        lifecycle_parent_context="",
        environ=environ,
        plugin_root=tmp_path / "plugin",
        fallback_pid=999,
    )

    assert result.exit_code == 1
    assert "BOOTSTRAP_STAGE=model-read\n" in result.stdout
    assert len(runner.calls) == 3
