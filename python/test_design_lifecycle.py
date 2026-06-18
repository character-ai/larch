"""Tests for Python /design lifecycle helpers."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import design_lifecycle
import design_pause
from design_lifecycle import load_bash_quoted_env, phase_driver_read_result_env


CLI = Path(__file__).with_name("cli.py")


def test_phase_driver_read_result_env_filters_allowlist_and_cr(tmp_path: Path) -> None:
    env = tmp_path / "result.env"
    env.write_bytes(b"INIT_STATUS=ok\nSECRET=drop\nRUN_PARAMS_PATH=/tmp/run.json\nBAD=has\r\n")  # pyright: ignore[reportUnusedCallResult]
    assert phase_driver_read_result_env(env, ["INIT_STATUS", "RUN_PARAMS_PATH", "BAD"]) == [
        ("INIT_STATUS", "ok"),
        ("RUN_PARAMS_PATH", "/tmp/run.json"),
    ]


def test_phase_driver_read_result_env_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    target.write_text("INIT_STATUS=ok\n", encoding="utf-8")  # pyright: ignore[reportUnusedCallResult]
    link = tmp_path / "link.env"
    link.symlink_to(target)
    with pytest.raises(OSError, match="not a regular file"):
        phase_driver_read_result_env(link, ["INIT_STATUS"])  # pyright: ignore[reportUnusedCallResult]


def test_design_read_result_env_cli_writes_sourceable_output(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    output = tmp_path / "out.env"
    source.write_text("INIT_STATUS=ok\nRUN_PARAMS_PATH=Bob's run\nSECRET=drop\n", encoding="utf-8")  # pyright: ignore[reportUnusedCallResult]
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "design",
            "read-result-env",
            "--input",
            str(source),
            "--allow",
            "INIT_STATUS",
            "--allow",
            "RUN_PARAMS_PATH",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "INIT_STATUS='ok'" in output.read_text(encoding="utf-8")
    assert "RUN_PARAMS_PATH='Bob'\"'\"'s run'" in output.read_text(encoding="utf-8")


def test_design_route_merges_flags_for_already_planned(tmp_path: Path) -> None:
    body = tmp_path / "issue-body.md"
    _ = body.write_text("x\n<!-- larch:plan:start -->\nplan\n<!-- larch:plan:end -->\n", encoding="utf-8")
    run_params = tmp_path / "run-params.json"
    _ = run_params.write_text(
        '{"partition_requested": false, "brainstorm_requested": false, "approve_requested": false, "skip_approve_requested": false}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "design",
            "route",
            "--design-tmpdir",
            str(tmp_path),
            "--issue",
            "42",
            "--issue-title",
            "Feature request",
            "--issue-body-file",
            str(body),
            "--has-clarify-label",
            "false",
            "--claude-pid",
            "123",
            "--session-id",
            "run-1",
            "--partition-requested",
            "true",
            "--approve-requested",
            "true",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "ROUTE=already-planned" in result.stdout
    merged = json.loads(run_params.read_text(encoding="utf-8"))
    assert merged["partition_requested"] is True
    assert merged["approve_requested"] is True


def test_design_driver_emit_plan_is_rerunnable(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 5\n", encoding="utf-8")
    actions = tmp_path / "actions.txt"
    _ = actions.write_text("ACTION=EMIT_PLAN\nACTION=FINALIZE\n", encoding="utf-8")
    first = subprocess.run(
        [sys.executable, str(CLI), "design", "driver", "--design-tmpdir", str(design), "--action-file", str(actions)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0
    assert "STEP_COMPLETED=FINALIZE" in first.stdout
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 9\n", encoding="utf-8")
    second = subprocess.run(
        [sys.executable, str(CLI), "design", "driver", "--design-tmpdir", str(design), "--action-file", str(actions)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0
    assert "STEP_STARTED=EMIT_PLAN" in second.stdout
    assert "STEP_SKIPPED=FINALIZE REASON=already-completed" in second.stdout



def run_design_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, "LARCH_QUIET_DISABLE": "1", "CLAUDE_PLUGIN_ROOT": str(CLI.parent.parent)}
    if env:
        merged.update(env)
    return subprocess.run([sys.executable, str(CLI), "design", *args], capture_output=True, text=True, check=False, env=merged)


def test_step0_parse_writes_bash_quoted_cache_and_round_trips_verbal(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = run_design_cli("step0-parse", "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--", "--brainstorm", "hello world", env={"HOME": str(home)})
    assert result.returncode == 0, result.stderr
    assert "BRAINSTORM_REQUESTED=true" in result.stdout
    assert "POSITIONAL_KIND=verbal" in result.stdout
    assert "POSITIONAL_VALUE=hello world" in result.stdout
    cache = home / ".cache" / "larch" / "sessions" / "step0-parsed-123.env"
    text = cache.read_text(encoding="utf-8")
    assert "POSITIONAL_VALUE=hello\\ world" in text
    assert load_bash_quoted_env(cache, ["POSITIONAL_VALUE"])["POSITIONAL_VALUE"] == "hello world"


def test_step0_parse_rejects_template_literal(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = run_design_cli("step0-parse", "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--", "${PUBLIC_ARGV_WORDS}", env={"HOME": str(home)})
    assert result.returncode == 1
    assert "skill loader did not expand public argv words" in result.stderr


def test_step0c_pause_save_precedes_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(f"export DESIGN_TMPDIR={design}\nexport ISSUE_NUMBER=42\nexport CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")

    def fake_pause(argv: list[str]) -> int:
        (design / "pause-called").write_text(" ".join(argv), encoding="utf-8")
        return 11

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0c_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert exc.value.code == 11
    assert (design / "pause-called").is_file()
    assert not (design / ".completed" / "step-0c").exists()


def test_step1e_reentry_removes_expected_sentinels(tmp_path: Path) -> None:
    design = tmp_path / "design"
    completed = design / ".completed"
    completed.mkdir(parents=True)
    for name in ("step-1e", "step-2a", "step-2a.5", "step-2b", "step-2b.5", "step-3", "step-3.5", "step-3b", "step-4", "step-4b", "step-keep"):
        (completed / name).write_text("", encoding="utf-8")
    (design / ".gate-b-postapply-ready-x").write_text("", encoding="utf-8")
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(f"export DESIGN_TMPDIR={design}\nexport CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    assert design_lifecycle.step1e_reentry_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]) == 0
    assert (completed / "step-keep").exists()
    assert not (completed / "step-2a.5").exists()
    assert not (design / ".gate-b-postapply-ready-x").exists()
