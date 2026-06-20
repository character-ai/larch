"""Tests for Python /design lifecycle helpers."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

import config
import design_lifecycle
import design_pause
import design_publish
import logging_util
import proc as proc_module
import stall_recovery
from design_lifecycle import load_bash_quoted_env, phase_driver_read_result_env


CLI = Path(__file__).with_name("cli.py")


def _fake_parse_none(*_args: object, **_kwargs: object) -> tuple[int, dict[str, str], str]:
    return (
        0,
        {
            "POSITIONAL_KIND": "none",
            "partition_requested": "false",
            "brainstorm_requested": "false",
            "approve_requested": "false",
            "skip_approve_requested": "false",
            "no_dedup_requested": "false",
            "run_id": "",
            "POSITIONAL_VALUE": "",
        },
        "",
    )


def _fake_read_json_issue_title(*_args: object, **_kwargs: object) -> tuple[str, str, str]:
    return ("Title", "body", "false")


def _fake_read_json_issue_t(*_args: object, **_kwargs: object) -> tuple[str, str, str]:
    return ("T", "body", "false")


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


def test_decode_bash_percent_q_decodes_utf8_byte_escaped_emoji() -> None:
    assert design_lifecycle._decode_bash_percent_q("$'\\360\\237\\230\\200'") == "😀"  # pyright: ignore[reportPrivateUsage]


def test_decode_bash_percent_q_decodes_utf8_byte_escaped_accent() -> None:
    assert design_lifecycle._decode_bash_percent_q("$'caf\\303\\251'") == "café"  # pyright: ignore[reportPrivateUsage]


def test_decode_bash_percent_q_malformed_utf8_byte_escape_is_safe() -> None:
    assert design_lifecycle._decode_bash_percent_q("$'\\377'") == "ÿ"  # pyright: ignore[reportPrivateUsage]


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


@pytest.mark.parametrize(
    "value",
    [
        "hello world",
        "Bob's \"quoted\"",
        "dollar$sign",
        "line1\nline2",
        "tab\there",
    ],
)
def test_bash_quoted_env_round_trips_metacharacters(tmp_path: Path, value: str) -> None:
    cache = tmp_path / "parsed.env"
    design_lifecycle.write_bash_quoted_env(cache, {"POSITIONAL_VALUE": value, "POSITIONAL_KIND": "verbal"})
    loaded = load_bash_quoted_env(cache, ["POSITIONAL_VALUE"])
    assert loaded["POSITIONAL_VALUE"] == value


def test_step0_parse_allows_verbal_containing_public_argv_words_substring(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = run_design_cli(
        "step0-parse",
        "--claude-pid",
        "123",
        "--plugin-root",
        str(CLI.parent.parent),
        "--",
        "feature about PUBLIC_ARGV_WORDS in description",
        env={"HOME": str(home)},
    )
    assert result.returncode == 0, result.stderr
    assert "POSITIONAL_KIND=verbal" in result.stdout


def test_pause_save_main_accepts_wrapper_argv_without_cli_prefix(tmp_path: Path) -> None:
    rc = design_pause.pause_save_main(["--design-tmpdir", str(tmp_path), "--issue", "0"])
    assert rc == 0


def test_pause_save_receives_only_flag_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(
        f"export DESIGN_TMPDIR={design}\nexport ISSUE_NUMBER=42\nexport CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n",
        encoding="utf-8",
    )
    captured: list[list[str]] = []

    def capture_pause(argv: list[str]) -> int:
        captured.append(list(argv))
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", capture_pause)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0c_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert exc.value.code == 0
    assert captured == [["--design-tmpdir", str(design), "--issue", "42"]]


def test_require_design_tmpdir_rejects_missing(tmp_path: Path) -> None:
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0c_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert exc.value.code == 1


def test_require_design_tmpdir_rejects_relative_path(tmp_path: Path) -> None:
    env_path = tmp_path / "source-env.sh"
    env_path.write_text("export DESIGN_TMPDIR=relative/path\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0c_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert exc.value.code == 1


def test_relay_degraded_tools_gate_stdout_both_down_seen_guard(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    stdout = "DEGRADED=true\nBOTH_DOWN=false\n"
    state = design_lifecycle.relay_degraded_tools_gate_stdout(stdout, design)
    assert state["BOTH_DOWN_SEEN"] == "true"
    assert state["STEP0_STATUS"] == "needs-degraded-decision"


def test_relay_degraded_tools_gate_stdout_degraded_one_down_with_prompt(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".degraded-tools-gate-prompted").write_text("", encoding="utf-8")
    stdout = "DEGRADED=true\nBOTH_DOWN=false\n"
    state = design_lifecycle.relay_degraded_tools_gate_stdout(stdout, design)
    assert state["STEP0_STATUS"] == "degraded-one-down"


def test_step0_session_parse_kvs_precede_session_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    stale = home / ".cache" / "larch" / "sessions" / "step0-parsed-123.env"
    stale.parent.mkdir(parents=True)
    stale.write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=99\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)

    def fake_setup(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "SESSION_TMPDIR=" + str(design) + "\nSESSION_ID=run-1\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\nCODEX_PRESENT=false\nCURSOR_PRESENT=false\n", "")

    def fake_gate(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "DEGRADED=false\nBOTH_DOWN=false\n", "")

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        if "session" in joined and "setup" in joined:
            return fake_setup(cmd, **kwargs)
        if "degraded-tools-gate" in joined:
            return fake_gate(cmd, **kwargs)
        if "write-design-env" in joined:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_run_parse_argv", _fake_parse_none)

    buf = StringIO()
    with redirect_stdout(buf):
        rc = design_lifecycle.step0_session_main(["--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--"])
    stdout = buf.getvalue()
    assert rc == 0
    parse_idx = stdout.index("POSITIONAL_KIND=none")
    session_idx = stdout.index("SESSION_TMPDIR=")
    assert parse_idx < session_idx


def _write_session_env(tmp_path: Path, design: Path, monkeypatch: pytest.MonkeyPatch | None = None, **extra: str) -> Path:
    resolved = design.resolve()
    if monkeypatch is not None:
        monkeypatch.setenv("DESIGN_TMPDIR", str(resolved))
    env_path = tmp_path / "source-env.sh"
    lines = [
        f"export DESIGN_TMPDIR={resolved}",
        "export SESSION_ID=run-1",
        f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}",
    ]
    lines.extend(f"export {key}={value}" for key, value in extra.items())
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def test_step0_route_cancel_pause_load_replays_errors_and_no_route_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    (design / ".design-route-result.env").write_text("ROUTE=cancel-pause-load\nERROR=pause-load-broken\nWARN=stale-marker\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "ROUTE=cancel-pause-load\nERROR=pause-load-broken\nWARN=stale-marker\n", "")

    monkeypatch.setattr(subprocess, "run", fake_route)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "ERROR=pause-load-broken" in captured.out
    assert "WARN=stale-marker" in captured.out
    assert not any(line.startswith("ROUTE=") for line in captured.out.splitlines())


def test_step0_route_relays_stderr_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=none\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 2, "", "design-route.sh: issue-body-file must be a readable regular file\n")

    monkeypatch.setattr(subprocess, "run", fake_route)

    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "issue-body-file must be a readable regular file" in captured.err


def test_step0_init_preserves_spaced_issue_title(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=none\n", encoding="utf-8")
    (design / ".design-step0-route-state.env").write_text("ROUTE=proceed\nISSUE_TITLE=Add retry support\nISSUE_NUMBER=42\n", encoding="utf-8")
    (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body text\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42")

    def fake_init(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (design / ".design-init-runparams-result.env").write_text("INIT_STATUS=ok\nRENAMED=false\nRUN_PARAMS_PATH=" + str(design / "run-params.json") + "\n", encoding="utf-8")
        (design / "run-params.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "INIT_STATUS=ok\nRENAMED=false\n", "")

    monkeypatch.setattr(subprocess, "run", fake_init)

    assert design_lifecycle.step0_init_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]) == 0
    feature = (design / "feature-description.txt").read_text(encoding="utf-8")
    assert feature.startswith("# Add retry support\n\n")


def test_step0_init_skips_feature_write_when_route_result_differs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=none\n", encoding="utf-8")
    (design / ".design-step0-route-state.env").write_text("ROUTE=proceed\nISSUE_TITLE=Stale\n", encoding="utf-8")
    (design / ".design-route-result.env").write_text("ROUTE=clarify\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_init(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (design / ".design-init-runparams-result.env").write_text("INIT_STATUS=ok\nRENAMED=false\nRUN_PARAMS_PATH=" + str(design / "run-params.json") + "\n", encoding="utf-8")
        (design / "run-params.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_init)

    assert design_lifecycle.step0_init_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]) == 0
    assert not (design / "feature-description.txt").exists()


def test_step0_init_relays_stderr_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=none\n", encoding="utf-8")
    (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_init(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (design / ".design-init-runparams-result.env").write_text("INIT_STATUS=env-refresh-failed\nRUN_PARAMS_PATH=\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 1, "", "design-init-runparams.sh: missing required arguments\n")

    monkeypatch.setattr(subprocess, "run", fake_init)

    rc = design_lifecycle.step0_init_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "missing required arguments" in captured.err


def test_step0_clarify_hard_halt_forwards_exit_code_and_detail_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    detail = design / "custom.failure.log"
    detail.write_text("detail\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42")
    captured: list[list[str]] = []

    def fake_stage(argv: list[str]) -> tuple[int, list[str]]:
        captured.append(list(argv))
        print("STAGED=true")
        return 0, ["STAGED=true"]

    monkeypatch.setattr(design_lifecycle, "stage_terminal_state_core", fake_stage)

    assert design_lifecycle.step0_clarify_hard_halt_main(
        [
            "--session-env-path",
            str(env_path),
            "--claude-pid",
            "123",
            "--plugin-root",
            str(CLI.parent.parent),
            "--exit-code",
            "7",
            "--failure-detail-log",
            str(detail),
        ]
    ) == 0
    argv = captured[0]
    assert "--exit-code" in argv
    assert argv[argv.index("--exit-code") + 1] == "7"
    assert "--failure-detail-log" in argv
    assert str(detail) in argv[argv.index("--failure-detail-log") + 1]
    assert "STAGED=true" in (design / "design-stage-terminal-state.stdout.log").read_text(encoding="utf-8")


def _stage_args(design: Path, *extra: str) -> list[str]:
    return [
        "--design-tmpdir",
        str(design.resolve()),
        "--outcome",
        "failed-clarify",
        "--step",
        "clarify",
        "--phase",
        "clarify-loop",
        "--site",
        "clarify-loop",
        "--trigger",
        "failed",
        "--bail-reason",
        "clarify-hard-halt",
        "--exit-code",
        "1",
        "--source-script",
        "clarify-loop",
        "--summary-outcome",
        "failed-clarify",
        *extra,
    ]


def test_stage_terminal_state_core_writes_state_and_rejects_bad_tokens(tmp_path: Path) -> None:
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path))
    assert rc == 0
    state = tmp_path / "design-failure-terminal-state.env"
    assert state.is_file()
    assert "FAILURE_OUTCOME=failed-clarify" in state.read_text(encoding="utf-8")

    bad_rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path / "missing", "--evidence-ref", "../unsafe"))
    assert bad_rc == 2


def test_stage_terminal_state_preserves_mismatched_existing_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state = tmp_path / "design-failure-terminal-state.env"
    state.write_text(
        "DESIGN_FAILURE_VERSION=1\nDESIGN_FAILURE_KIND=terminal\nFAILURE_OUTCOME=failed-publish\nSTALL_STEP=publish\nPHASE=publish\nSITE=design-publish\nTRIGGER=publish-tail-failed\nBAIL_REASON=publish-tail-failed\nEXIT_CODE=1\nFAILURE_DETAIL_LOG=\nSOURCE_SCRIPT=design-step5c\nOCCURRED_AT=2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path))
    assert rc == 0
    assert "PRESERVED=true" in capsys.readouterr().out


def test_capture_contract_stream_restores_parent_stdout_stderr(tmp_path: Path) -> None:
    out = tmp_path / "stdout.log"
    err = tmp_path / "stderr.log"

    def emit_contract() -> int:
        logging_util.emit_kv("CAPTURED", "true")
        print("stderr-row", file=sys.stderr)
        return 0

    assert design_lifecycle.capture_contract_stream_to_paths(emit_contract, out, err) == 0
    os.write(1, b"")
    os.write(2, b"")
    assert "CAPTURED=true" in out.read_text(encoding="utf-8")
    assert "stderr-row" in err.read_text(encoding="utf-8")


def test_failure_report_core_sentinel_and_cancellation_paths(tmp_path: Path) -> None:
    (tmp_path / "design-failure-terminal-report.env").write_text("", encoding="utf-8")
    rc, _ = design_lifecycle.failure_report_core(["--design-tmpdir", str(tmp_path.resolve()), "--outcome", "failed-clarify"])
    assert rc == 0
    (tmp_path / "design-failure-terminal-report.env").unlink()
    rc, _ = design_lifecycle.failure_report_core(["--design-tmpdir", str(tmp_path.resolve()), "--outcome", "cancelled-user"])
    assert rc == 0
    assert (tmp_path / "design-failure-operator-action-chat.md").is_file()


def test_step_final_summary_core_emits_markers_and_cleans_bg_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary without newline", encoding="utf-8")

    def fake_render(argv: list[str]) -> int:
        assert "--post-publish-only" in argv
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" in out
    assert "summary without newline\nLARCH_FINAL_SUMMARY_END" in out
    assert not (tmp_path / ".bg-wait-active").exists()
    assert (tmp_path / ".completed" / "step-final-summary").is_file()


def test_step0_route_forwards_router_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text(
        "POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\npartition_requested=true\nbrainstorm_requested=true\napprove_requested=true\nskip_approve_requested=true\n",
        encoding="utf-8",
    )
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="T", HAS_CLARIFY_LABEL="false", REPO="owner/repo", SESSION_ID="sid-1")
    captured: list[list[str]] = []

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")

    monkeypatch.setattr(subprocess, "run", fake_route)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_t)

    assert design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]) == 0
    route_cmd = captured[0]
    for flag, value in (
        ("--partition-requested", "true"),
        ("--brainstorm-requested", "true"),
        ("--approve-requested", "true"),
        ("--skip-approve-requested", "true"),
        ("--claude-pid", "123"),
        ("--session-id", "sid-1"),
        ("--repo", "owner/repo"),
    ):
        assert flag in route_cmd
        assert route_cmd[route_cmd.index(flag) + 1] == value


def test_step1d5_collect_pause_precedes_collect(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42")
    order: list[str] = []

    def fake_pause(_argv: list[str]) -> int:
        order.append("pause")
        return 3

    def fake_collect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        order.append("collect")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    monkeypatch.setattr(subprocess, "run", fake_collect)
    out_path = design / "cursor-brainstorm-output.txt"
    out_path.write_text("x\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step1d5_main(
            ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--", str(out_path)]
        )
    assert exc.value.code == 3
    assert order == ["pause"]


def test_step1d5_collect_launch_failure_sentinel_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    out_path = design / "cursor-brainstorm-output.txt"
    out_path.write_text("x\n", encoding="utf-8")
    sink = design / "cursor-brainstorm-launch.failure.log"
    sink.write_text("LAUNCHER_EXIT=2\n", encoding="utf-8")
    append_calls = 0

    def fake_append(*_a: object, **_k: object) -> bool:
        nonlocal append_calls
        append_calls += 1
        return True

    def fake_collect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def fake_checkpoint(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(design_lifecycle, "_append_failure", fake_append)
    monkeypatch.setattr(subprocess, "run", fake_collect)
    monkeypatch.setattr(design_lifecycle, "_brainstorm_dirty_checkpoint", fake_checkpoint)
    args = ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--", str(out_path)]
    assert design_lifecycle.step1d5_main(args) == 0
    assert append_calls == 1
    assert (design / ".brainstorm-cursor-brainstorm-launch.failure.log.runlog-appended").is_file()
    assert design_lifecycle.step1d5_main(args) == 0
    assert append_calls == 1


def test_step0_parse_rejects_rc3_validation_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    def fake_parse(*_args: object, **_kwargs: object) -> tuple[int, dict[str, str], str]:
        return (3, {"VALIDATION_ERROR": "bad flag", "POSITIONAL_KIND": "none"}, "")

    monkeypatch.setattr(design_lifecycle, "_run_parse_argv", fake_parse)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0_parse_main(["--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--"])
    assert exc.value.code == 1
    assert "unrecognized or disallowed public flag" in capsys.readouterr().err
    assert not (home / ".cache" / "larch" / "sessions" / "step0-parsed-123.env").exists()


def test_step0_parse_rejects_rc0_with_validation_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    def fake_parse(*_args: object, **_kwargs: object) -> tuple[int, dict[str, str], str]:
        return (0, {"VALIDATION_ERROR": "stale", "POSITIONAL_KIND": "none"}, "")

    monkeypatch.setattr(design_lifecycle, "_run_parse_argv", fake_parse)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0_parse_main(["--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--"])
    assert exc.value.code == 1
    assert "VALIDATION_ERROR but exited 0" in capsys.readouterr().err


def test_step0_parse_rejects_invalid_positional_kind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    def fake_parse(*_args: object, **_kwargs: object) -> tuple[int, dict[str, str], str]:
        return (0, {"POSITIONAL_KIND": "bogus", "POSITIONAL_VALUE": ""}, "")

    monkeypatch.setattr(design_lifecycle, "_run_parse_argv", fake_parse)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0_parse_main(["--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--"])
    assert exc.value.code == 1
    assert "invalid POSITIONAL_KIND" in capsys.readouterr().err


def test_step0_abort_cleanup_appends_failure_and_cleans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(f"export DESIGN_TMPDIR={design}\nexport CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    calls: list[str] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        calls.append(joined)
        if "append-failure" in joined:
            (design / "execution-issues.md").write_text("### Warnings\n- degraded-tools-gate\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = design_lifecycle.step0_abort_cleanup_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert rc == 0
    assert "aborted by operator" in capsys.readouterr().out
    assert any("append-failure" in call for call in calls)
    assert any("cleanup-tmpdir" in call for call in calls)
    assert (design / "execution-issues.md").is_file()


def test_step0_ap_continue_writes_sentinels_before_pause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_pause(_argv: list[str]) -> int:
        completed = design / ".completed"
        for name in ("step-1c", "step-1d", "step-1d.5"):
            assert (completed / name).is_file(), f"missing sentinel {name} before pause"
        return 5

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0_ap_continue_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert exc.value.code == 5


@pytest.mark.parametrize(
    ("run_params", "expected"),
    [
        ('{"skip_approve_requested": true}', "true"),
        ('{"skip_approve_requested": false}', "false"),
        ("{}", "false"),
        ("not-json", "false"),
    ],
)
def test_step1d7_emits_skip_approve_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    run_params: str,
    expected: str,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "run-params.json").write_text(run_params + "\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    buf = StringIO()
    with redirect_stdout(buf):
        rc = design_lifecycle.step1d7_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    assert rc == 0
    assert f"SKIP_APPROVE_REQUESTED={expected}" in buf.getvalue()


def test_step0_session_fails_on_degraded_gate_nonzero_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    monkeypatch.setenv("HOME", str(home))

    def fake_setup(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "SESSION_TMPDIR=" + str(design) + "\nSESSION_ID=run-1\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\nCODEX_PRESENT=false\nCURSOR_PRESENT=false\n", "")

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        if "session" in joined and "setup" in joined:
            return fake_setup(cmd, **kwargs)
        if "degraded-tools-gate" in joined:
            return subprocess.CompletedProcess(cmd, 9, "", "argparse: bad flag")
        if "write-design-env" in joined:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_run_parse_argv", _fake_parse_none)

    buf = StringIO()
    with redirect_stdout(buf):
        rc = design_lifecycle.step0_session_main(["--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--"])
    assert rc == 9
    assert "STEP0_STATUS=" not in buf.getvalue()
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "degraded-tools gate: subprocess exited 9" in issues


def test_step1d5_collect_rejects_missing_paths(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design)
    rc = design_lifecycle.step1d5_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--"])
    assert rc == 2


def test_step1d5_collect_relays_per_slot_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design)
    framing = design / "cursor-brainstorm-output.txt"
    scope = design / "codex-brainstorm-output.txt"
    framing.write_text("framing text", encoding="utf-8")
    scope.write_text("scope text", encoding="utf-8")
    captured_paths: list[str] = []

    def fake_collect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        paths = [part for part in cmd if part.endswith(".txt")]
        captured_paths.extend(paths)
        stdout = "\n".join(f"COLLECTED:{Path(path).name}:{Path(path).read_text(encoding='utf-8')}" for path in paths)
        return subprocess.CompletedProcess(cmd, 0, stdout + "\n", "")

    def fake_checkpoint(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "STATUS=clean\n", "")

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        if "collect-results" in joined:
            return fake_collect(cmd, **kwargs)
        if "dirty-tree" in joined and "checkpoint" in joined:
            return fake_checkpoint(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert design_lifecycle.step1d5_main(
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--", str(framing), str(scope)]
    ) == 0
    assert captured_paths == [str(framing), str(scope)]
    out = capsys.readouterr().out
    assert "COLLECTED:cursor-brainstorm-output.txt:framing text" in out
    assert "COLLECTED:codex-brainstorm-output.txt:scope text" in out


def test_step1d5_collect_records_nonzero_collector_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design)
    out_path = design / "cursor-brainstorm-output.txt"
    out_path.write_text("collector input", encoding="utf-8")
    append_calls: list[tuple[str, int | str]] = []

    def fake_append(_plugin_root: Path, design_tmpdir: Path, _site: str, tool: str, exit_code: int | str, category: str, _output_file: Path) -> bool:
        append_calls.append((tool, exit_code))
        (design_tmpdir / "execution-issues.md").write_text(f"### {category}\n- {tool} exited {exit_code}\n", encoding="utf-8")
        return True

    def fake_collect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 23, "collector stdout fixture\n", "collector stderr fixture\n")

    def fake_checkpoint(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "STATUS=clean\n", "")

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        if "collect-results" in joined:
            return fake_collect(cmd, **kwargs)
        if "dirty-tree" in joined and "checkpoint" in joined:
            return fake_checkpoint(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(design_lifecycle, "_append_failure", fake_append)
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert design_lifecycle.step1d5_main(
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--", str(out_path)]
    ) == 0
    failure_log = (design / "brainstorm-collect.failure.log").read_text(encoding="utf-8")
    assert "collector stdout fixture" in failure_log
    assert "collector stderr fixture" in failure_log
    assert append_calls == [("agent collect-results", 23)]
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "agent collect-results exited 23" in issues


def test_step1d5_collect_merges_dirty_tree_sidecars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design)
    dirty_a = design / "cursor-brainstorm-output.txt"
    dirty_b = design / "codex-brainstorm-output.txt"
    dirty_a.write_text("", encoding="utf-8")
    dirty_b.write_text("", encoding="utf-8")
    dirty_a.with_name(dirty_a.name + ".dirty-tree").write_text("STATUS=clean\n", encoding="utf-8")
    dirty_b.with_name(dirty_b.name + ".dirty-tree").write_text("STATUS=dirty\n", encoding="utf-8")

    def fake_collect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def fake_checkpoint(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "STATUS=clean\n", "")

    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: fake_collect(cmd, **kwargs) if "collect-results" in " ".join(cmd) else fake_checkpoint(cmd, **kwargs))  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    assert design_lifecycle.step1d5_main(
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--", str(dirty_a), str(dirty_b)]
    ) == 0
    detected = (design / "dirty-tree-detected.env").read_text(encoding="utf-8")
    assert "STAGE=brainstorm-collection" in detected
    assert "RECOVERY_REQUIRED=true" in detected
    assert "DIRTY_TREE_STATUS=dirty" in detected


def test_step1d5_collect_records_clean_dirty_tree_checkpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design)
    clean_a = design / "cursor-brainstorm-output.txt"
    clean_a.write_text("", encoding="utf-8")

    def fake_collect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def fake_checkpoint(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, "STATUS=clean\n", "")

    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: fake_collect(cmd, **kwargs) if "collect-results" in " ".join(cmd) else fake_checkpoint(cmd, **kwargs))  # type: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
    assert design_lifecycle.step1d5_main(
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "collect", "--", str(clean_a)]
    ) == 0
    detected = (design / "dirty-tree-detected.env").read_text(encoding="utf-8")
    assert "RECOVERY_REQUIRED=false" in detected
    assert "DIRTY_TREE_STATUS=" not in detected


def test_resolve_repo_parses_ssh_url_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **_kwargs: object) -> object:
        if argv[:2] == ["gh", "repo"]:
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()
        if argv[:3] == ["git", "remote", "get-url"]:
            return type("R", (), {"returncode": 0, "stdout": "ssh://git@github.com/org/repo.git\n", "stderr": ""})()
        raise AssertionError(f"unexpected argv: {argv}")

    monkeypatch.setattr(proc_module, "run", fake_run)
    assert design_lifecycle.resolve_repo() == "org/repo"


def test_step0_route_rejects_non_numeric_issue_positional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=abc\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "POSITIONAL_KIND=issue requires numeric POSITIONAL_VALUE" in captured.err


def test_step0_route_rejects_invalid_positional_kind_from_parsed_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=bogus\nPOSITIONAL_VALUE=\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "invalid POSITIONAL_KIND=bogus" in captured.err


def test_step0_route_rejects_verbal_without_issue_number(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=verbal\nPOSITIONAL_VALUE=feature text\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "POSITIONAL_KIND=verbal requires ISSUE_NUMBER" in captured.err


def test_step0_route_enables_brainstorm_from_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Brainstorm: feature", HAS_CLARIFY_LABEL="false", REPO="owner/repo")

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (design / ".design-route-result.env").write_text("ROUTE=proceed\nBRAINSTORM_PREFIX=true\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\nBRAINSTORM_PREFIX=true\n", "")

    monkeypatch.setattr(subprocess, "run", fake_route)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "auto-enabling brainstorm mode" in captured.out
    state = (design / ".design-step0-route-state.env").read_text(encoding="utf-8")
    assert "brainstorm_requested=true" in state


def test_step0_route_emits_resume_step_kvs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (design / ".design-route-result.env").write_text("ROUTE=resume@2a\nMARKER_CLEARED=step-2a\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "ROUTE=resume@2a\nMARKER_CLEARED=step-2a\n", "")

    monkeypatch.setattr(subprocess, "run", fake_route)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "ROUTE=resume@2a" in captured.out
    assert "RESUME_STEP=2a" in captured.out
    assert "MARKER_CLEARED=step-2a" in captured.out


def test_step0_route_preserves_pre_set_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="preset/repo")
    captured: list[list[str]] = []

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")

    monkeypatch.setattr(subprocess, "run", fake_route)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)
    monkeypatch.setattr(design_lifecycle, "resolve_repo", lambda: "resolved/repo")

    assert design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]) == 0
    route_cmd = captured[0]
    assert "--repo" in route_cmd
    assert route_cmd[route_cmd.index("--repo") + 1] == "preset/repo"


def test_step0_session_relays_stderr_only_setup_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        joined = " ".join(cmd)
        if "session" in joined and "setup" in joined:
            return subprocess.CompletedProcess(cmd, 1, "session setup failed: missing repo\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_run_parse_argv", _fake_parse_none)

    buf = StringIO()
    with redirect_stdout(buf):
        rc = design_lifecycle.step0_session_main(["--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "session setup failed: missing repo" in buf.getvalue() + captured.out


def test_relay_degraded_tools_gate_stdout_negative_both_down_seen_guard(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".degraded-tools-gate-prompted").write_text("", encoding="utf-8")
    stdout = "DEGRADED=true\n"
    state = design_lifecycle.relay_degraded_tools_gate_stdout(stdout, design)
    assert state["BOTH_DOWN_SEEN"] == "false"
    assert state["STEP0_STATUS"] == "needs-degraded-decision"


def test_step0_init_wrapper_stdout_stays_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=none\n", encoding="utf-8")
    (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_init(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        (design / ".design-init-runparams-result.env").write_text(
            "INIT_STATUS=ok\nRENAMED=false\nRUN_PARAMS_PATH=" + str(design / "run-params.json") + "\n",
            encoding="utf-8",
        )
        (design / "run-params.json").write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "INIT_STATUS=ok\nRENAMED=false\n", "")

    monkeypatch.setattr(subprocess, "run", fake_init)

    rc = design_lifecycle.step0_init_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "INIT_STATUS=" not in captured.out
    assert "RENAMED=" not in captured.out


def test_step1d5_entry_writes_sentinels_before_pause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_pause(_argv: list[str]) -> int:
        completed = design / ".completed"
        for name in ("step-1c", "step-1d"):
            assert (completed / name).is_file(), f"missing sentinel {name} before pause"
        return 4

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step1d5_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "entry"])
    assert exc.value.code == 4


def test_step1d5_complete_writes_step_1d5_before_pause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_pause(_argv: list[str]) -> int:
        assert (design / ".completed" / "step-1d.5").is_file()
        return 6

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step1d5_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent), "--mode", "complete"])
    assert exc.value.code == 6


def test_wrapper_loads_design_current_env_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    sessions = home / ".cache" / "larch" / "sessions"
    sessions.mkdir(parents=True)
    design = tmp_path / "design"
    design.mkdir()
    source = design / "source-env.sh"
    source.write_text(
        f"export DESIGN_TMPDIR={design.resolve()}\nexport ISSUE_NUMBER=42\nexport CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n",
        encoding="utf-8",
    )
    link = sessions / "current-design-env-123.sh"
    link.symlink_to(source)
    monkeypatch.setenv("HOME", str(home))
    assert design_lifecycle.step0c_main(["--session-env-path", str(link), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]) == 0
    assert (design / ".completed" / "step-0c").is_file()


def test_bash_quoted_env_round_trips_non_ascii_verbal(tmp_path: Path) -> None:
    value = "café"
    cache = tmp_path / "parsed.env"
    design_lifecycle.write_bash_quoted_env(cache, {"POSITIONAL_VALUE": value, "POSITIONAL_KIND": "verbal"})
    loaded = load_bash_quoted_env(cache, ["POSITIONAL_VALUE"])
    assert loaded["POSITIONAL_VALUE"] == value


def test_step2a_repairs_sentinels_without_plugin_root(tmp_path: Path) -> None:
    (tmp_path / "run-params.json").write_text('{"brainstorm_requested": false}\n', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CLI), "design", "step2a"],
        capture_output=True,
        text=True,
        env={"DESIGN_TMPDIR": str(tmp_path), "CLAUDE_PLUGIN_ROOT": ""},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "approach-synthesis.txt").read_text(encoding="utf-8") == "NO_SKETCHES\n"
    assert (tmp_path / "contested-decisions.md").read_text(encoding="utf-8") == "NO_CONTESTED_DECISIONS\n"
    assert (tmp_path / "dialectic-resolutions.md").read_text(encoding="utf-8") == ""
    assert (tmp_path / ".completed" / "step-2a").is_file()
    assert (tmp_path / ".completed" / "step-1d.5").is_file()


def test_step2a_refuses_conflicting_sentinel_artifacts(tmp_path: Path) -> None:
    (tmp_path / "approach-synthesis.txt").write_text("real sketch\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CLI), "design", "step2a"],
        capture_output=True,
        text=True,
        env={"DESIGN_TMPDIR": str(tmp_path), "CLAUDE_PLUGIN_ROOT": ""},
        check=False,
    )
    assert result.returncode == 1
    assert "sentinel repair refused" in result.stderr


def test_wrapper_session_env_parser_exports_quoted_paths(tmp_path: Path) -> None:
    design = tmp_path / "design dir"
    design.mkdir()
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(
        f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='42'\nexport CLAUDE_PLUGIN_ROOT={str(Path.cwd())!r}\n",
        encoding="utf-8",
    )
    parsed = design_lifecycle._parse_common_wrapper_args(["--session-env-path", str(session_env)])  # pyright: ignore[reportPrivateUsage]
    merged = design_lifecycle._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    assert merged["DESIGN_TMPDIR"] == str(design)
    assert os.environ["ISSUE_NUMBER"] == "42"


def test_step2b_postplan_nonfatal_rc_10_exits_zero_and_emits_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "plan.txt").write_text("bad\n", encoding="utf-8")
    (tmp_path / ".step2b-plan-source").write_text("drafter\n", encoding="utf-8")

    def fake_emit(_argv: list[str]) -> int:
        (tmp_path / ".design-postplan-emit-result.env").write_text(
            "VALIDATE_STATUS=defects-found\nVALIDATE_DEFECT_COUNT=1\nVALIDATE_SKIPPED_COUNT=0\nVALIDATE_UNSAFE_TOKEN_COUNT=0\nVALIDATE_LOG_FILE=log\n",
            encoding="utf-8",
        )
        print("POSTPLAN_EMIT_STATUS=ok")
        return 10

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "POSTPLAN_RC=10" in out
    assert "POSTPLAN_STATUS=validate-failed" in out
    assert "SCOUT_STALE_CLEARED=true" in out
    assert (tmp_path / ".step2b-postplan-inline-retry-done").is_file()


def test_step2b5_echoes_check_size_stdout_and_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_check(_argv: list[str]) -> int:
        print("PLAN_SIZE_STATUS=failed")
        return 7

    monkeypatch.setattr(design_lifecycle.plan_quality, "check_plan_size_main", fake_check)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))
    rc = design_lifecycle.step2b5_main([])
    assert rc == 7
    assert "PLAN_SIZE_STATUS=failed" in capsys.readouterr().out


def test_step2_launcher_argv_rehydrates_wrapper_env(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(
        f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='42'\n",
        encoding="utf-8",
    )
    rc = design_lifecycle.step2a_main(["--session-env-path", str(session_env), "--claude-pid", "123"])
    assert rc == 0
    assert os.environ["DESIGN_TMPDIR"] == str(design)
    assert os.environ["ISSUE_NUMBER"] == "42"


def test_step2a_rejects_missing_design_tmpdir(tmp_path: Path) -> None:
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step2a_main(["--session-env-path", str(session_env), "--claude-pid", "123"])
    assert exc.value.code == 1


def test_step2a_rejects_relative_design_tmpdir(tmp_path: Path) -> None:
    session_env = tmp_path / "session-env.sh"
    session_env.write_text("export DESIGN_TMPDIR=relative/path\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step2a_main(["--session-env-path", str(session_env), "--claude-pid", "123"])
    assert exc.value.code == 1


def test_rehydrate_wrapper_env_resolves_trusted_design_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    sessions = home / ".cache" / "larch" / "sessions"
    sessions.mkdir(parents=True)
    source = sessions / "design-env-123.sh"
    design = tmp_path / "design"
    design.mkdir()
    source.write_text(f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='7'\n", encoding="utf-8")
    link = sessions / "current-design-env-123.sh"
    link.symlink_to(source)
    monkeypatch.setenv("HOME", str(home))
    parsed = design_lifecycle._parse_common_wrapper_args(["--session-env-path", str(link), "--claude-pid", "123"])  # pyright: ignore[reportPrivateUsage]
    merged = design_lifecycle._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    assert merged["DESIGN_TMPDIR"] == str(design)
    assert merged["ISSUE_NUMBER"] == "7"


def test_step2a_accepts_sentinel_without_trailing_newline(tmp_path: Path) -> None:
    (tmp_path / "approach-synthesis.txt").write_text("NO_SKETCHES", encoding="utf-8")
    (tmp_path / "contested-decisions.md").write_text("NO_CONTESTED_DECISIONS\n", encoding="utf-8")
    (tmp_path / "dialectic-resolutions.md").write_text("", encoding="utf-8")
    assert design_lifecycle._valid_step2b_sentinels(tmp_path)  # pyright: ignore[reportPrivateUsage]


def test_step2a_accepts_legacy_sentinel_with_newline(tmp_path: Path) -> None:
    (tmp_path / "run-params.json").write_text('{"brainstorm_requested": false}\n', encoding="utf-8")
    (tmp_path / "approach-synthesis.txt").write_text("NO_SKETCHES_CLASSIFIED_SIMPLE\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(CLI), "design", "step2a"],
        capture_output=True,
        text=True,
        env={"DESIGN_TMPDIR": str(tmp_path), "CLAUDE_PLUGIN_ROOT": ""},
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_step2b_drafter_pause_before_fallback_seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "approach-synthesis.txt").write_text("NO_SKETCHES\n", encoding="utf-8")
    (design / "contested-decisions.md").write_text("NO_CONTESTED_DECISIONS\n", encoding="utf-8")
    (design / "dialectic-resolutions.md").write_text("", encoding="utf-8")
    (design / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    (design / ".pause-requested").write_text("", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", lambda _d: 11)  # type: ignore[arg-type]
    rc = design_lifecycle.step2b_drafter_main([])
    out = capsys.readouterr().out
    assert rc == 11
    assert "POSTPLAN_RC=11" in out
    assert "POSTPLAN_STATUS=pause-save" in out
    assert not (design / ".step2b-postplan-fallback-used").exists()


@pytest.mark.parametrize("vendor", ["codex", "claude"])
def test_step2b_drafter_launcher_uses_python_cli_argv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    vendor: str,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "approach-synthesis.txt").write_text("NO_SKETCHES\n", encoding="utf-8")
    (design / "contested-decisions.md").write_text("NO_CONTESTED_DECISIONS\n", encoding="utf-8")
    (design / "dialectic-resolutions.md").write_text("", encoding="utf-8")
    (design / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", vendor)
    monkeypatch.setenv("LARCH_DESIGN_PLAN_MODEL", "claude-test-model")
    captured: list[list[str]] = []

    def fake_run(
        argv: Sequence[object],
        *,
        text: bool = False,
        capture_output: bool = False,
        check: bool = False,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del text, capture_output, check
        args = [str(item) for item in argv]
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=" M existing.txt\n", stderr="")
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=str(CLI.parent.parent) + "\n", stderr="")
        if args[2:4] == ["agent", f"launch-{vendor}-drafter"]:
            captured.append(args)
            (design / "plan.txt").write_text("## Plan\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("STATUS=ok\nPLAN_WRITTEN=true\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def fake_postplan(_args: design_lifecycle.WrapperArgs) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(0, "", "ok")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    assert len(captured) == 1
    argv = captured[0]
    expected_verb = f"launch-{vendor}-drafter"
    assert argv[:4] == [sys.executable, str(CLI), "agent", expected_verb]
    for flag in (
        "--prompt-file",
        "--output-file",
        "--baseline-porcelain",
        "--timeout",
        "--timing-task-kind",
        "--design-tmpdir",
        "--repo-root",
    ):
        assert flag in argv
    if vendor == "claude":
        assert "--model" in argv
    else:
        assert "--model" not in argv
    assert not any(token.endswith(".sh") for token in argv)


def test_step2b5_pause_short_circuit_skips_check_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    called = False

    def fake_check(_argv: list[str]) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(design_lifecycle.plan_quality, "check_plan_size_main", fake_check)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", lambda _d: 11)  # type: ignore[arg-type]
    rc = design_lifecycle.step2b5_main([])
    assert rc == 11
    assert called is False


def test_step2b_postplan_rc_11_raises_system_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", lambda _d: 11)  # type: ignore[arg-type]
    with pytest.raises(SystemExit) as exc:
        design_lifecycle._shared_step2b_postplan_body(design_lifecycle.WrapperArgs(site="step2b"))  # pyright: ignore[reportPrivateUsage]
    assert exc.value.code == 11


def test_step2b_postplan_rc_12_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_emit(_argv: list[str]) -> int:
        return 12

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "POSTPLAN_RC=12" in out
    assert "POSTPLAN_STATUS=plan-size-trigger" in out
    assert (tmp_path / ".completed" / "step-2b").is_file()


def test_step2b_postplan_rc_13_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_emit(_argv: list[str]) -> int:
        return 13

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "POSTPLAN_RC=13" in out
    assert "POSTPLAN_STATUS=partition-requested" in out


def test_step2b_postplan_fatal_emit_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_emit(_argv: list[str]) -> int:
        return 2

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    assert rc == 1


def test_step2b_postplan_gate_b_ignores_snapshot_original_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_emit(argv: list[str]) -> int:
        seen.extend(argv)
        return 0

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    design_lifecycle.step2b_postplan_main(["--site", "gate-b", "--snapshot-original"])
    assert "--snapshot-original" not in seen


def _judge_panel_stage_args(design: Path, *extra: str) -> list[str]:
    return [
        "--design-tmpdir",
        str(design.resolve()),
        "--outcome",
        "failed-judge-panel",
        "--step",
        "judge-panel",
        "--phase",
        "judge-panel",
        "--site",
        "decompose-panel",
        "--trigger",
        "decompose-panel-retry-exhausted",
        "--bail-reason",
        "decompose-panel-retry-exhausted",
        "--exit-code",
        "1",
        "--source-script",
        "split-path",
        "--summary-outcome",
        "failed-judge-panel",
        *extra,
    ]


def _panel_init_stage_args(design: Path, detail_log: Path) -> list[str]:
    return [
        "--design-tmpdir",
        str(design.resolve()),
        "--outcome",
        "failed-judge-panel",
        "--step",
        "judge-panel",
        "--phase",
        "judge-panel",
        "--site",
        "step3-review",
        "--trigger",
        "panel-init-failed",
        "--bail-reason",
        "panel-init-failed",
        "--exit-code",
        "1",
        "--source-script",
        "design-step3-review",
        "--failure-detail-log",
        str(detail_log),
        "--summary-outcome",
        "failed-judge-panel",
    ]


def _stage_terminal_for_report(tmp_path: Path, outcome: str = "failed-clarify") -> None:
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path, "--outcome", outcome, "--summary-outcome", outcome))
    assert rc == 0


def _capture_failure_report(tmp_path: Path, outcome: str, monkeypatch: pytest.MonkeyPatch | None = None) -> tuple[int, str, str]:
    if monkeypatch is not None:
        real_run_stall: Callable[..., int] = design_lifecycle._run_stall_main  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType, reportUnknownVariableType]

        def fake_stall(
            callable_obj: object,
            argv: list[str],
            *,
            stdout_path: Path | None = None,
            stderr_path: Path | None = None,
        ) -> int:
            if callable_obj is stall_recovery.compose_report_main:
                if stdout_path is not None:
                    stdout_path.write_text("STALL_RECOVERY_REPORT_STATUS=filed\nSTALL_RECOVERY_REPORT_ARTIFACT=artifact.md\n", encoding="utf-8")
                return 0
            if callable_obj is stall_recovery.populate_sensitive_corpus_main:
                return 0
            if callable_obj is stall_recovery.validate_terminal_state_main:
                return real_run_stall(callable_obj, argv, stdout_path=stdout_path, stderr_path=stderr_path)
            if callable_obj is stall_recovery.init_attempts_main:
                return 0
            if callable_obj is stall_recovery.classify_main and stdout_path is not None:
                stdout_path.write_text("", encoding="utf-8")
                return 0
            return real_run_stall(callable_obj, argv, stdout_path=stdout_path, stderr_path=stderr_path)

        monkeypatch.setattr(design_lifecycle, "_run_stall_main", fake_stall)  # pyright: ignore[reportPrivateUsage]
    out = tmp_path / "failure-report.stdout.log"
    err = tmp_path / "failure-report.stderr.log"
    rc = design_lifecycle.capture_contract_stream_to_paths(
        design_lifecycle.failure_report_core,
        out,
        err,
        ["--design-tmpdir", str(tmp_path.resolve()), "--outcome", outcome],
    )
    return rc, out.read_text(encoding="utf-8"), err.read_text(encoding="utf-8")


def test_stage_terminal_state_rejects_unknown_outcome_and_vocab(tmp_path: Path) -> None:
    bad_outcome = _stage_args(tmp_path, "--outcome", "bad-outcome")
    assert design_lifecycle.stage_terminal_state_core(bad_outcome)[0] == 2
    bad_step = _stage_args(tmp_path, "--step", "nope")
    assert design_lifecycle.stage_terminal_state_core(bad_step)[0] == 2


def test_stage_terminal_state_rejects_non_numeric_exit_code(tmp_path: Path) -> None:
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path, "--exit-code", "abc"))
    assert rc == 2


def test_stage_terminal_state_accepts_unknown_exit_code(tmp_path: Path) -> None:
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path, "--exit-code", "unknown"))
    assert rc == 0
    state = (tmp_path / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    assert "EXIT_CODE=unknown" in state


def test_stage_terminal_state_rejects_outside_and_symlink_detail_log(tmp_path: Path) -> None:
    outside_dir = Path(tempfile.mkdtemp())
    try:
        outside = outside_dir / "outside.log"
        outside.write_text("safe\n", encoding="utf-8")
        rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path, "--failure-detail-log", str(outside)))
        assert rc == 2
    finally:
        shutil.rmtree(outside_dir, ignore_errors=True)
    inside = tmp_path / "evidence.log"
    inside.write_text("safe\n", encoding="utf-8")
    link = tmp_path / "evidence.link"
    link.symlink_to(inside)
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path, "--failure-detail-log", str(link)))
    assert rc == 2


def test_stage_terminal_state_rejects_symlink_existing_state(tmp_path: Path) -> None:
    target = tmp_path / "state.env"
    target.write_text("DESIGN_FAILURE_VERSION=1\nFAILURE_OUTCOME=failed-clarify\nSITE=clarify-loop\nTRIGGER=failed\n", encoding="utf-8")
    link = tmp_path / "design-failure-terminal-state.env"
    link.symlink_to(target)
    rc, _ = design_lifecycle.stage_terminal_state_core(_stage_args(tmp_path))
    assert rc == 2


def test_stage_terminal_state_stages_failed_judge_panel_decompose(tmp_path: Path) -> None:
    rc, _ = design_lifecycle.stage_terminal_state_core(_judge_panel_stage_args(tmp_path))
    assert rc == 0
    state = (tmp_path / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    assert "SITE=decompose-panel" in state
    assert "TRIGGER=decompose-panel-retry-exhausted" in state


def test_stage_terminal_state_stages_panel_init_failed_bail(tmp_path: Path) -> None:
    detail = tmp_path / "step3-panel-init-failed.log"
    detail.write_text("panel init failed\n", encoding="utf-8")
    rc, _ = design_lifecycle.stage_terminal_state_core(_panel_init_stage_args(tmp_path, detail))
    assert rc == 0
    state = (tmp_path / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    assert "BAIL_REASON=panel-init-failed" in state


def test_stage_terminal_state_main_rejects_disallowed_tmpdir(capsys: pytest.CaptureFixture[str]) -> None:
    try:
        disallowed = Path(tempfile.mkdtemp(prefix="larch-test-terminal-disallowed.", dir="/var/tmp"))
    except OSError:
        pytest.skip("/var/tmp unavailable for disallowed tmpdir case")
    try:
        rc = design_lifecycle.stage_terminal_state_main(_stage_args(disallowed))
        captured = capsys.readouterr()
        assert rc == 2
        assert "allowlist" in captured.err.lower()
    finally:
        shutil.rmtree(disallowed, ignore_errors=True)


def test_capture_contract_stream_restores_fd3_for_quiet_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "stdout.log"
    err = tmp_path / "stderr.log"
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_DESIGN_TMPDIR, str(tmp_path))

    def emit_contract() -> int:
        logging_util.emit_kv("CAPTURED", "true")
        return 0

    assert design_lifecycle.capture_contract_stream_to_paths(emit_contract, out, err) == 0
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        logging_util.quiet_init(argv0="parent-quiet")
        logging_util.emit_kv("POST_CAPTURE", "ok")
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 4096).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert "POST_CAPTURE=ok" in contract


def test_failure_report_missing_terminal_state_fallback(tmp_path: Path) -> None:
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-clarify")
    assert "DESIGN_FAILURE_REPORT_DECISION=fallback-print-required" in stdout
    assert (tmp_path / "design-failure-chat-print.md").is_file()


def test_failure_report_terminal_success_and_sentinel_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stage_terminal_for_report(tmp_path)
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-clarify", monkeypatch)
    assert "DESIGN_FAILURE_REPORT_DECISION=terminal-failure" in stdout
    assert (tmp_path / "design-failure-terminal-report.env").is_file()
    _, second, _ = _capture_failure_report(tmp_path, "failed-clarify", monkeypatch)
    assert "DESIGN_FAILURE_REPORT_REASON=terminal-sentinel-present" in second


def test_failure_report_terminal_compose_failed_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stage_terminal_for_report(tmp_path)
    real_run_stall: Callable[..., int] = design_lifecycle._run_stall_main  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType, reportUnknownVariableType]

    def fake_stall(
        callable_obj: object,
        argv: list[str],
        *,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> int:
        if callable_obj is stall_recovery.compose_report_main:
            return 1
        if callable_obj is stall_recovery.populate_sensitive_corpus_main:
            return 0
        if callable_obj is stall_recovery.validate_terminal_state_main:
            return real_run_stall(callable_obj, argv, stdout_path=stdout_path, stderr_path=stderr_path)
        if callable_obj is stall_recovery.init_attempts_main:
            return 0
        if callable_obj is stall_recovery.classify_main and stdout_path is not None:
            stdout_path.write_text("", encoding="utf-8")
            return 0
        return real_run_stall(callable_obj, argv, stdout_path=stdout_path, stderr_path=stderr_path)

    monkeypatch.setattr(design_lifecycle, "_run_stall_main", fake_stall)  # pyright: ignore[reportPrivateUsage]
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-clarify")
    assert "DESIGN_FAILURE_REPORT_DECISION=fallback-print-required" in stdout
    assert "DESIGN_FAILURE_REPORT_REASON=terminal-compose-failed" in stdout
    audit = tmp_path / "design-failure-audit.log"
    assert audit.is_file()
    assert "terminal-compose-failed" in audit.read_text(encoding="utf-8")


def test_failure_report_compose_status_reads_last_matching_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stage_terminal_for_report(tmp_path)
    real_run_stall: Callable[..., int] = design_lifecycle._run_stall_main  # pyright: ignore[reportPrivateUsage, reportUnknownMemberType, reportUnknownVariableType]

    def fake_stall(
        callable_obj: object,
        argv: list[str],
        *,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
    ) -> int:
        if callable_obj is stall_recovery.compose_report_main:
            if stdout_path is not None:
                stdout_path.write_text(
                    "STALL_RECOVERY_REPORT_STATUS=printed\nSTALL_RECOVERY_REPORT_STATUS=filed\nSTALL_RECOVERY_REPORT_ARTIFACT=artifact.md\n",
                    encoding="utf-8",
                )
            return 0
        if callable_obj is stall_recovery.populate_sensitive_corpus_main:
            return 0
        if callable_obj is stall_recovery.validate_terminal_state_main:
            return real_run_stall(callable_obj, argv, stdout_path=stdout_path, stderr_path=stderr_path)
        if callable_obj is stall_recovery.init_attempts_main:
            return 0
        if callable_obj is stall_recovery.classify_main and stdout_path is not None:
            stdout_path.write_text("", encoding="utf-8")
            return 0
        return real_run_stall(callable_obj, argv, stdout_path=stdout_path, stderr_path=stderr_path)

    monkeypatch.setattr(design_lifecycle, "_run_stall_main", fake_stall)  # pyright: ignore[reportPrivateUsage]
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-clarify")
    assert "DESIGN_FAILURE_REPORT_DECISION=terminal-failure" in stdout


def test_failure_report_outcome_mismatch_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stage_terminal_for_report(tmp_path, "failed-clarify")
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-publish", monkeypatch)
    assert "DESIGN_FAILURE_REPORT_DECISION=fallback-print-required" in stdout
    assert "DESIGN_FAILURE_REPORT_REASON=terminal-state-outcome-mismatch" in stdout


def test_failure_report_invalid_terminal_state_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stage_terminal_for_report(tmp_path)
    state = tmp_path / "design-failure-terminal-state.env"
    state.write_text(state.read_text(encoding="utf-8") + "INVALID=not-a-token\n", encoding="utf-8")
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-clarify", monkeypatch)
    assert "DESIGN_FAILURE_REPORT_DECISION=fallback-print-required" in stdout
    assert "DESIGN_FAILURE_REPORT_REASON=invalid-terminal-state" in stdout


def test_failure_report_escalation_success_from_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "design-failure-escalation-ledger.tsv"
    ledger.write_text(
        "utc=2026-01-01T00:00:00Z\tsite=step3-review\ttrigger=main-agent-vote-required\tstep=step3\tphase=validation\tdispatcher=design-step3-review\texit_code=unknown\tfailure_detail_log=\n",
        encoding="utf-8",
    )
    _, stdout, _ = _capture_failure_report(tmp_path, "approved", monkeypatch)
    assert "DESIGN_FAILURE_REPORT_DECISION=escalation-success" in stdout


def test_failure_report_failed_judge_panel_terminal_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rc, _ = design_lifecycle.stage_terminal_state_core(_judge_panel_stage_args(tmp_path))
    assert rc == 0
    _, stdout, _ = _capture_failure_report(tmp_path, "failed-judge-panel", monkeypatch)
    assert "DESIGN_FAILURE_REPORT_DECISION=terminal-failure" in stdout


def test_step_final_summary_pause_skips_bg_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (tmp_path / ".pause-requested").write_text("", encoding="utf-8")

    def fake_pause(_argv: list[str]) -> int:
        return 3

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    rc, _ = design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    assert rc == 3
    assert not (tmp_path / ".bg-wait-active").exists()


def test_step_final_summary_marker_failure_still_emits_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")
    (tmp_path / ".bg-wait-active").mkdir()

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_ok_marker(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(design_summary, "render_final_summary_main", render_ok_marker)
    rc, _ = design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "456", "--outcome", "approved"])
    assert rc == 0
    assert (tmp_path / ".completed" / "step-final-summary").is_file()
    assert "bg-wait marker setup failed" in (tmp_path / "execution-issues.md").read_text(encoding="utf-8")


def test_step_final_summary_render_exception_skips_sentinel_and_marked_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def boom(_argv: list[str]) -> int:
        raise RuntimeError("render broke")

    monkeypatch.setattr(design_summary, "render_final_summary_main", boom)
    rc, _ = design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    assert rc == 1
    assert not (tmp_path / ".completed" / "step-final-summary").is_file()
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in capsys.readouterr().out


def test_step_final_summary_main_returns_failure_without_sentinel_after_render_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_fail(_argv: list[str]) -> int:
        return 1

    monkeypatch.setattr(design_summary, "render_final_summary_main", render_fail)
    rc = design_lifecycle.step_final_summary_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    assert rc == 1
    assert not (tmp_path / ".completed" / "step-final-summary").is_file()


def test_step_final_summary_bg_marker_records_claude_pid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")
    seen: list[str] = []

    @contextlib.contextmanager
    def capture_marker(_design_tmpdir: object, _step: str, *, claude_pid: str = ""):
        seen.append(claude_pid)
        yield

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_ok(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(design_lifecycle, "_bg_wait_marker_context", capture_marker)
    monkeypatch.setattr(design_summary, "render_final_summary_main", render_ok)
    design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "789", "--outcome", "approved"])
    assert seen == ["789"]


def test_step_final_summary_emits_report_gate_sidecars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")
    (tmp_path / "design-failure-chat-print.md").write_text("chat sidecar\n", encoding="utf-8")

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_ok_sidecar(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(design_summary, "render_final_summary_main", render_ok_sidecar)
    design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    out = capsys.readouterr().out
    handoff = tmp_path / "design-report-gate-sidecars.md"
    assert handoff.is_file()
    assert "REPORT_GATE_SIDECARS_FILE=" in out
    assert str(handoff) in out


def test_step_final_summary_cli_subprocess_emits_markers_on_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("cli summary\n", encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(CLI.parent)
    env[config.ENV_DESIGN_TMPDIR] = str(tmp_path.resolve())
    env.pop(config.ENV_LARCH_QUIET_DISABLE, None)
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "design",
            "step-final-summary",
            "--session-env-path",
            str(env_path),
            "--claude-pid",
            "123",
            "--outcome",
            "approved",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" in result.stdout
    assert "LARCH_FINAL_SUMMARY_END" in result.stdout


def _setup_step5c_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: str) -> tuple[Path, Path]:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    env_path = _write_session_env(
        tmp_path,
        design,
        monkeypatch,
        ISSUE_NUMBER=extra.pop("ISSUE_NUMBER", "42"),
        SESSION_ID=extra.pop("SESSION_ID", "run-1"),
        **extra,
    )
    return design, env_path


def _step5c_rows(design: Path, *, plan_write_ok: str = "true", publish_ok: str = "true", final_summary: Path | None = None) -> str:
    summary = final_summary or (design / "final-summary.md")
    return "\n".join(
        [
            f"PLAN_WRITE_OK={plan_write_ok}",
            "VALIDATE_STATUS=ok",
            "VALIDATE_DEFECT_COUNT=0",
            "VALIDATE_SKIPPED_COUNT=0",
            "VALIDATE_UNSAFE_TOKEN_COUNT=0",
            "VALIDATE_LOG_FILE=",
            f"PUBLISH_OK={publish_ok}",
            "UPSERT_STATUS=ok",
            "ARCHITECTURE_SOURCE=new",
            f"FINAL_SUMMARY_PATH={summary}",
            "",
        ]
    )


def test_step5c_core_requires_design_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 1


def test_step5c_core_requires_step5b_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42")
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 1
    assert (design / ".completed" / "step-5c-terminal").is_file()


def test_step5c_core_pause_requested_skips_publish_and_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")
    called: list[list[str]] = []

    def fake_pause(argv: list[str]) -> int:
        called.append(argv)
        return 12

    def fail_publish(_argv: list[str]) -> int:
        raise AssertionError("publish_core should not run on pause")

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    monkeypatch.setattr(design_publish, "publish_core", fail_publish)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 12
    assert called == [["--design-tmpdir", str(design), "--issue", "42", "--repo", "owner/repo"]]
    assert not (design / ".bg-wait-active").exists()
    assert not (design / ".completed" / "step-5c-terminal").exists()


def test_step5c_core_pause_requested_emits_step5c_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")

    def fake_pause(_argv: list[str]) -> int:
        logging_util.emit_kv("PAUSE_OK", "true")
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5C_STATUS=pause-save" in out
    assert "PAUSE_OK=true" in out
    assert not (design / ".completed" / "step-5c-terminal").exists()


def test_step5c_core_assembles_publish_argv_and_cleans_bg_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-abc", REPO="owner/repo")
    seen: list[list[str]] = []

    def fake_publish(argv: list[str]) -> int:
        seen.append(argv)
        marker = design / ".bg-wait-active"
        assert marker.is_file()
        assert "STEP=design-step5c" in marker.read_text(encoding="utf-8")
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        print("unmarked render stdout")
        (design / "final-summary.md").write_text("summary body\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "777", "--skip-validate"])
    out = capsys.readouterr().out
    assert rc == 0
    assert seen == [
        [
            "--design-tmpdir",
            str(design),
            "--issue",
            "42",
            "--session-id",
            "run-abc",
            "--claude-pid",
            "777",
            "--repo",
            "owner/repo",
            "--skip-validate",
        ]
    ]
    assert not (design / ".bg-wait-active").exists()
    assert (design / ".completed" / "step-5c").is_file()
    assert (design / ".completed" / "step-5c-terminal").is_file()
    assert "PUBLISH_RC=0" in out
    assert "LARCH_FINAL_SUMMARY_BEGIN\nsummary body\nLARCH_FINAL_SUMMARY_END" in out
    assert "unmarked render stdout" not in out
    assert "unmarked render stdout" in (design / "render-final-summary.approved.stdout.log").read_text(encoding="utf-8")


def test_step5c_core_rc1_uses_stdout_over_stale_primary_and_binds_final_summary_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    stale = design / ".design-publish-result.env"
    stale.write_text("PLAN_WRITE_OK=true\nFINAL_SUMMARY_PATH=/stale/final-summary.md\nPUBLISH_OK=true\n", encoding="utf-8")
    current_summary = design / "current-summary.md"
    seen_env: list[str] = []

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design, plan_write_ok="false", publish_ok="", final_summary=current_summary), end="")
        current_summary.write_text("current failed summary\n", encoding="utf-8")
        return 1

    def fake_render(_argv: list[str]) -> int:
        seen_env.append(os.environ.get("FINAL_SUMMARY_PATH", ""))
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 0
    assert seen_env == [str(current_summary)]
    status = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "PLAN_WRITE_OK=false" in status
    assert "PUBLISH_STDOUT_FALLBACK=true" in status
    assert "CLEANUP_ELIGIBLE=false" in status
    assert not (design / ".completed" / "step-5c").exists()
    assert "current failed summary" in out


def test_step5c_core_rc3_stdout_fallback_keeps_success_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design), end="")
        return 3

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert (design / ".completed" / "step-5c").is_file()
    assert "PUBLISH_STDOUT_FALLBACK=true" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_rc4_emits_validator_status_sidecars_and_no_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / ".design-publish-result.env").write_text("PLAN_WRITE_OK=true\nVALIDATE_STATUS=ok\n", encoding="utf-8")
    (design / "design-failure-chat-print.md").write_text("sidecar body\n", encoding="utf-8")

    def fake_publish(_argv: list[str]) -> int:
        print(
            "\n".join(
                [
                    "PLAN_WRITE_OK=false",
                    "VALIDATE_STATUS=defects-found",
                    "VALIDATE_DEFECT_COUNT=2",
                    "VALIDATE_SKIPPED_COUNT=0",
                    "VALIDATE_UNSAFE_TOKEN_COUNT=1",
                    f"VALIDATE_LOG_FILE={design / 'validate.log'}",
                    f"FINAL_SUMMARY_PATH={design / 'final-summary.md'}",
                    "",
                ]
            ),
            end="",
        )
        return 4

    def fail_render(_argv: list[str]) -> int:
        raise AssertionError("render should not run for validator defects")

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fail_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5C_STATUS=validator-defects" in out
    assert "REPORT_GATE_SIDECARS_FILE=" in out
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in out
    assert "PLAN_WRITE_OK=false" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_publish_tail_abort_stages_renders_and_writes_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / "design-failure-operator-action-chat.md").write_text("operator sidecar\n", encoding="utf-8")

    def fake_publish(_argv: list[str]) -> int:
        return 2

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("abort summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 1
    assert (design / "design-failure-terminal-state.env").is_file()
    assert "FAILURE_OUTCOME=failed-publish-tail" in (design / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    stdout_log = design / "design-stage-terminal-state.stdout.log"
    stderr_log = design / "design-stage-terminal-state.stderr.log"
    assert stdout_log.is_file()
    assert stderr_log.is_file()
    assert stdout_log.stat().st_size > 0
    assert (design / ".completed" / "step-5c-terminal").is_file()
    assert "LARCH_FINAL_SUMMARY_BEGIN\nabort summary\nLARCH_FINAL_SUMMARY_END" in out
    assert "REPORT_GATE_SIDECARS_FILE=" in out


@pytest.mark.parametrize(
    ("session_id", "publish_ok", "expected_cleanup"),
    [
        ("", "", "true"),
        ("run-abc", "true", "true"),
        ("run-abc", "false", "false"),
        ("run-abc", "", "false"),
    ],
)
def test_step5c_core_cleanup_eligibility_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_id: str,
    publish_ok: str,
    expected_cleanup: str,
) -> None:
    design, env_path = _setup_step5c_design(
        tmp_path,
        monkeypatch,
        ISSUE_NUMBER="42",
        SESSION_ID=session_id,
        STANDALONE_HEAVY_FAILED="false",
    )

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design, publish_ok=publish_ok), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert f"CLEANUP_ELIGIBLE={expected_cleanup}" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_publish_tail_abort_rc5_stages_and_writes_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str]) -> int:
        return 5

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("abort summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 1
    assert (design / "design-failure-terminal-state.env").is_file()
    stdout_log = design / "design-stage-terminal-state.stdout.log"
    stderr_log = design / "design-stage-terminal-state.stderr.log"
    assert stdout_log.is_file()
    assert stderr_log.is_file()
    assert stdout_log.stat().st_size > 0
    assert (design / ".completed" / "step-5c-terminal").is_file()
    assert "LARCH_FINAL_SUMMARY_BEGIN\nabort summary\nLARCH_FINAL_SUMMARY_END" in out


def test_step5c_core_success_without_final_summary_skips_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    stale = design / "final-summary.md"
    stale.write_text("stale summary\n", encoding="utf-8")

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design, final_summary=design / "missing-summary.md"), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        stale.unlink()
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in out


def test_step5c_core_render_failure_skips_stale_summary_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / "final-summary.md").write_text("stale summary\n", encoding="utf-8")

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        return 1

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in out


def test_step5c_core_captures_subprocess_stdout_from_publish_tail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str]) -> int:
        os.write(1, b"WRITTEN=true\nMODE=write\n")
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PUBLISH_RC=0" in out
    assert "WRITTEN=true" not in out
    assert "MODE=write" not in out


def test_step5c_main_machine_rows_visible_under_inherited_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, "999999")
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = design_lifecycle.step5c_main(["--session-env-path", str(env_path), "--claude-pid", "123"])
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 65536).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert rc == 0
    assert "PUBLISH_RC=0" in contract
