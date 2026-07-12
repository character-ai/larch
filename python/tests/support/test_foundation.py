"""Focused tests for the shared test foundation."""

from __future__ import annotations

import pytest

from test_support import CLI, ROOT, RecordingRunner, completed, ok, repo_root


def test_ok_normalizes_arguments_and_preserves_stdout() -> None:
    result = ok(["git", "status"], "clean\n")

    assert result.argv == ("git", "status")
    assert result.returncode == 0
    assert result.stdout == "clean\n"
    assert result.stderr == ""
    assert result.duration == 0.01


def test_ok_defaults_to_empty_stdout() -> None:
    assert ok(("true",)).stdout == ""


def test_completed_preserves_arguments_and_stdout() -> None:
    argv = ["python3", "-V"]
    result = completed(argv, "Python 3.11\n")

    assert result.args is argv
    assert result.returncode == 0
    assert result.stdout == "Python 3.11\n"
    assert result.stderr == ""


def test_completed_defaults_to_empty_stdout() -> None:
    assert completed(("true",)).stdout == ""


def test_strict_queue_keeps_runner_state_isolated() -> None:
    first = RecordingRunner.strict_queue(ok(("first", "one")), ok(("first", "two")))
    second = RecordingRunner.strict_queue(ok(("second",)))

    assert first.run(("first",)).argv == ("first", "one")
    assert second.run(("second",)).argv == ("second",)
    assert first.run(("first",)).argv == ("first", "two")
    assert first.responses is not second.responses


def test_strict_queue_raises_after_responses_are_consumed() -> None:
    runner = RecordingRunner.strict_queue(ok(("git", "status")))

    _ = runner.run(("git", "status"))

    with pytest.raises(AssertionError, match="no response for call"):
        _ = runner.run(("git", "status"))


def test_default_queue_without_default_builds_success_for_call() -> None:
    result = RecordingRunner.default_queue().run(("git", "status"))

    assert result == ok(("git", "status"))


def test_default_queue_returns_explicit_default_after_exhaustion() -> None:
    default = ok(("default",), "fallback")
    runner = RecordingRunner.default_queue(default)

    assert runner.run(("git", "status")) is default


def test_repo_root_and_cli_use_shared_path_contract() -> None:
    assert repo_root() == ROOT
    assert repo_root() / "python" / "cli.py" == CLI
