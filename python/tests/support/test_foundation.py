"""Focused tests for the shared test foundation."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest

from test_support import (
    CLI,
    DESIGN_BASELINE_KEYS,
    IMPLEMENT_BASELINE_KEYS,
    ROOT,
    RecordingRunner,
    completed,
    make_design_tmpdir,
    make_implement_tmpdir,
    ok,
    repo_root,
    seed_feature_description,
    seed_plan,
    seed_run_params,
    write_design_source_env,
    write_session_env,
)
from tests.support import repo_contract, session


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
    assert repo_contract.ROOT == ROOT
    assert repo_contract.repo_root() == ROOT


def test_import_graph_is_one_way() -> None:
    assert not hasattr(repo_contract, "write_session_env")
    assert session.ROOT is ROOT
    assert "test_support" not in session.__name__


def test_make_implement_tmpdir_layout(tmp_path: Path) -> None:
    impl = make_implement_tmpdir(tmp_path)

    assert impl == tmp_path / "impl"
    assert impl.name == "impl"
    assert (impl / "plan.txt").read_text(encoding="utf-8") == "## Plan\n"
    assert (impl / "feature-description.txt").read_text(encoding="utf-8") == "feature\n"
    text = (impl / "session-env.sh").read_text(encoding="utf-8")
    assert text == (
        "CURSOR_PRESENT=false\n"
        "CODEX_BINARY_FOUND=true\n"
        "CURSOR_BINARY_FOUND=true\n"
        f"LARCH_CLAUDE_PLUGIN_ROOT={ROOT}\n"
        f"REPO_ROOT={ROOT}\n"
    )
    assert "CODEX_PRESENT=" not in text
    assert "\nCLAUDE_PLUGIN_ROOT=" not in text
    assert not text.startswith("CLAUDE_PLUGIN_ROOT=")
    assert not (impl / "run-params.json").exists()


def test_make_implement_tmpdir_optional_run_params(tmp_path: Path) -> None:
    impl = make_implement_tmpdir(tmp_path, run_params=True)
    data = json.loads((impl / "run-params.json").read_text(encoding="utf-8"))
    assert data == {
        "schema_version": 3,
        "partition_requested": False,
        "brainstorm_requested": False,
        "approve_requested": False,
        "skip_approve_requested": False,
        "difficulty_override": "",
    }


def test_write_session_env_override_replace_and_additive_keys(tmp_path: Path) -> None:
    path = write_session_env(
        tmp_path,
        overrides={
            "CURSOR_PRESENT": "true",
            "MODE": "N/A",
            "REPO": "o/r",
            "WORKFLOW_PATH": "/tmp/wf",
            "LARCH_RUN_ID": "run-1",
        },
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith("CURSOR_PRESENT=true\n")
    assert f"LARCH_CLAUDE_PLUGIN_ROOT={ROOT}\n" in text
    assert "LARCH_RUN_ID=run-1\n" in text
    assert "MODE=N/A\n" in text
    assert "REPO=o/r\n" in text
    assert "WORKFLOW_PATH=/tmp/wf\n" in text
    # Additive keys are sorted after the baseline block.
    assert text.index("LARCH_RUN_ID=") < text.index("MODE=") < text.index("REPO=") < text.index("WORKFLOW_PATH=")


def test_write_session_env_omit_and_sparse_fixture(tmp_path: Path) -> None:
    path = write_session_env(
        tmp_path,
        omit=IMPLEMENT_BASELINE_KEYS,
        overrides={"REPO": "o/r", "MODE": "N/A"},
    )
    assert path.read_text(encoding="utf-8") == "MODE=N/A\nREPO=o/r\n"


def test_write_session_env_rejects_override_omit_conflict(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="override/omit conflict"):
        _ = write_session_env(tmp_path, overrides={"REPO_ROOT": "/x"}, omit={"REPO_ROOT"})


def test_write_session_env_rejects_malformed_keys_and_unsafe_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid environment key"):
        _ = write_session_env(tmp_path, overrides={"bad-key": "x"})
    with pytest.raises(ValueError, match="unsafe environment value"):
        _ = write_session_env(tmp_path, overrides={"MODE": "a\nb"})
    with pytest.raises(ValueError, match="unsafe environment value"):
        _ = write_session_env(tmp_path, overrides={"MODE": "a\rb"})
    with pytest.raises(ValueError, match="unsafe environment value"):
        _ = write_session_env(tmp_path, overrides={"MODE": "a\x00b"})


def test_presence_keys_independent_from_binary_found(tmp_path: Path) -> None:
    path = write_session_env(
        tmp_path,
        overrides={"CODEX_PRESENT": "true", "CURSOR_PRESENT": "false"},
    )
    text = path.read_text(encoding="utf-8")
    assert "CODEX_BINARY_FOUND=true\n" in text
    assert "CURSOR_BINARY_FOUND=true\n" in text
    assert "CODEX_PRESENT=true\n" in text
    assert "CURSOR_PRESENT=false\n" in text


def test_make_design_tmpdir_contract(tmp_path: Path) -> None:
    design = make_design_tmpdir(tmp_path)
    assert design == tmp_path / "design"
    text = (design / "source-env.sh").read_text(encoding="utf-8")
    assert text == (
        "#!/usr/bin/env bash\n"
        "# /design session env — generated by session_env.py. Do not edit.\n"
        f"export DESIGN_TMPDIR={shlex.quote(str(design))}\n"
        f"export SESSION_TMPDIR={shlex.quote(str(design))}\n"
        "export SESSION_ID=test-session\n"
        f"export REPO_ROOT={shlex.quote(str(ROOT))}\n"
        f"export CLAUDE_PLUGIN_ROOT={shlex.quote(str(ROOT))}\n"
    )
    assert not (design / "run-params.json").exists()


def test_write_design_source_env_rejects_non_writer_keys(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        _ = write_design_source_env(tmp_path, overrides={"MODE": "N/A"})
    with pytest.raises(ValueError, match="not allowed"):
        _ = write_design_source_env(tmp_path, overrides={"LARCH_CLAUDE_PLUGIN_ROOT": str(ROOT)})


def test_write_design_source_env_override_and_omit(tmp_path: Path) -> None:
    path = write_design_source_env(
        tmp_path,
        overrides={"REPO": "owner/repo", "SESSION_ID": "sid-9"},
        omit={"CLAUDE_PLUGIN_ROOT"},
    )
    text = path.read_text(encoding="utf-8")
    assert "export SESSION_ID=sid-9\n" in text
    assert "export REPO=owner/repo\n" in text
    assert "CLAUDE_PLUGIN_ROOT" not in text
    assert set(DESIGN_BASELINE_KEYS) >= {"DESIGN_TMPDIR", "SESSION_TMPDIR", "SESSION_ID", "REPO_ROOT"}


def test_seed_helpers_and_paths_with_spaces(tmp_path: Path) -> None:
    spaced = tmp_path / "dir with spaces"
    plan = seed_plan(spaced, "custom plan\n")
    feature = seed_feature_description(spaced, "custom feature\n")
    params = seed_run_params(spaced)
    assert plan.read_text(encoding="utf-8") == "custom plan\n"
    assert feature.read_text(encoding="utf-8") == "custom feature\n"
    assert json.loads(params.read_text(encoding="utf-8"))["schema_version"] == 3
    env_path = write_session_env(spaced, overrides={"WORKFLOW_PATH": str(spaced / "wf path")})
    assert f"WORKFLOW_PATH={spaced / 'wf path'}\n" in env_path.read_text(encoding="utf-8")


def test_isolated_parameterized_tmpdirs(tmp_path: Path) -> None:
    first = make_implement_tmpdir(tmp_path / "a")
    second = make_implement_tmpdir(tmp_path / "b", overrides={"LARCH_RUN_ID": "b"})
    assert first != second
    assert "LARCH_RUN_ID=" not in (first / "session-env.sh").read_text(encoding="utf-8")
    assert "LARCH_RUN_ID=b\n" in (second / "session-env.sh").read_text(encoding="utf-8")
