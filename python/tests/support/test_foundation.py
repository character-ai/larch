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
from tests.support.design_wire import (
    diff_lines_trailer,
    plan_body,
    result_env_lines,
    run_params_json,
    write_result_env,
)
from tests.support.review_wire import (
    ballot_snippet,
    make_finding_block,
    make_rejected_block,
    panel_manifest_ndjson,
    panel_manifest_row,
    plan_review_slot_line,
    slot_manifest_ndjson,
    vote_lines,
)
from tests.support.session import run_params_text


def test_review_wire_builders_preserve_canonical_fixture_shapes(tmp_path: Path) -> None:
    finding = make_finding_block(
        "FINDING_1",
        "Concern",
        reviewer=["codex-a", "cursor-b"],
        concern="The concern.",
        suggested_revision="Fix it.",
    )

    assert ballot_snippet(finding, make_finding_block("OOS_1", "Future", reviewer="cursor-c")) == (
        "### FINDING_1: Concern\n"
        "- **Reviewer(s)**: codex-a, cursor-b\n"
        "- **Concern**: The concern.\n"
        "- **Suggested revision**: Fix it.\n\n"
        "### OOS_1: Future\n"
        "- **Reviewer**: cursor-c\n"
    )
    assert make_rejected_block("FINDING_2", "Title", location="a.py:2", concern="Fix it.") == (
        "### [Plan Review] FINDING_2\n\n"
        "### FINDING_2: Title\n"
        "- **Location**: a.py:2\n"
        "- **Concern**: Fix it.\n"
        "- **Severity**: major\n\n"
    )
    assert vote_lines({"FINDING_1": "YES", "OOS_1": "NO"}) == "FINDING_1: YES\nOOS_1: NO\n"

    output = tmp_path / "output with spaces.txt"
    row = plan_review_slot_line(
        "codex-arch",
        "codex",
        output,
        prompt_file=tmp_path / "prompt.txt",
        vendor="codex",
        resolved_model="model",
    )
    expected = (
        '{"slot":"codex-arch","tool":"codex","output":"'
        + str(output)
        + '","prompt_file":"'
        + str(tmp_path / "prompt.txt")
        + '","vendor":"codex","resolved_model":"model"}\n'
    )
    assert slot_manifest_ndjson([row]) == expected
    assert panel_manifest_ndjson([panel_manifest_row("codex-arch", "codex", output)]) == (
        '{"slot":"codex-arch","tool":"codex","output":"' + str(output) + '"}\n'
    )
    unusual_row = plan_review_slot_line(
        "codex-β",
        "codex",
        tmp_path / 'output "quoted"\\path.txt',
        vendor='vendor "β"\\path',
    )
    unusual_manifest = slot_manifest_ndjson([unusual_row])
    assert "\\u03b2" not in unusual_manifest
    assert json.loads(unusual_manifest) == {
        "slot": "codex-β",
        "tool": "codex",
        "output": str(tmp_path / 'output "quoted"\\path.txt'),
        "vendor": 'vendor "β"\\path',
    }
    assert slot_manifest_ndjson([]) == ""


def test_design_wire_builders_preserve_canonical_fixture_shapes(tmp_path: Path) -> None:
    assert plan_body(sections=[("NEW", "a.py"), ("UPDATED", "b.py")], body="body", diff_lines=1) == (
        "## Plan\n"
        "### NEW: a.py\n"
        "### UPDATED: b.py\n"
        "body\n"
        "diff_lines: 1\n"
    )
    assert plan_body(body="Do the thing.", diff_lines=3, difficulty="MODERATE") == (
        "## Plan\n"
        "\n"
        "Do the thing.\n"
        "difficulty: MODERATE\n"
        "diff_lines: 3\n"
    )
    assert plan_body(header="# Plan", diff_lines=1) == "# Plan\n\ndiff_lines: 1\n"
    assert diff_lines_trailer(12, diff_added=10, diff_deleted=2, mechanical_churn=False) == (
        "diff_added: 10\n"
        "diff_deleted: 2\n"
        "mechanical_churn: false\n"
        "diff_lines: 12\n"
    )

    spaced = tmp_path / "dir with spaces"
    spaced.mkdir()
    env_path = spaced / "result.env"
    text = result_env_lines({"ROUTE": "proceed", "RUN_PARAMS_PATH": str(spaced / "run-params.json")})
    assert text == (
        "ROUTE=proceed\n"
        f"RUN_PARAMS_PATH={spaced / 'run-params.json'}\n"
    )
    written = write_result_env(env_path, [("INIT_STATUS", "ok"), ("OUTPUT", str(spaced / "β-out.txt"))])
    assert written.read_text(encoding="utf-8") == f"INIT_STATUS=ok\nOUTPUT={spaced / 'β-out.txt'}\n"

    defaults = run_params_json()
    assert defaults == run_params_text()
    assert defaults == seed_run_params(spaced).read_text(encoding="utf-8")
    overridden = run_params_json(overrides={"brainstorm_requested": True, "partition_requested": True})
    assert '"brainstorm_requested": true' in overridden
    assert '"partition_requested": true' in overridden
    assert overridden.endswith("\n")
    # Overrides must not mutate the shared default payload.
    assert json.loads(run_params_json())["brainstorm_requested"] is False

    with pytest.raises(ValueError, match="invalid environment key"):
        _ = result_env_lines({"bad-key": "x"})
    with pytest.raises(ValueError, match="unsafe environment value"):
        _ = result_env_lines({"ROUTE": "a\nb"})
    with pytest.raises(ValueError, match="unsafe environment value"):
        _ = result_env_lines({"ROUTE": "a\rb"})
    with pytest.raises(ValueError, match="unsafe environment value"):
        _ = result_env_lines({"ROUTE": "a\x00b"})
    link = tmp_path / "link.env"
    target = tmp_path / "target.env"
    _ = target.write_text("OLD=1\n", encoding="utf-8")
    link.symlink_to(target)
    with pytest.raises(OSError, match="symlink"):
        _ = write_result_env(link, {"ROUTE": "proceed"})


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
