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

from larch.core import config
import design_dialectic
from larch.design import design_lifecycle
from larch.design import design_pause
import design_publish
from larch.core import logging_util
from larch.core import proc as proc_module
from larch.state import session_env
from larch.state import stall_recovery
from larch.design.design_lifecycle import load_bash_quoted_env, phase_driver_read_result_env


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


def _step0_wrapper_args(env_path: Path) -> list[str]:
    return ["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)]


def _write_ok_init_result(design: Path, *, brainstorm_requested: bool = False) -> None:
    (design / ".design-init-runparams-result.env").write_text(
        "INIT_STATUS=ok\nRENAMED=false\nRUN_PARAMS_PATH=" + str(design / "run-params.json") + "\n",
        encoding="utf-8",
    )
    (design / "run-params.json").write_text(json.dumps({"brainstorm_requested": brainstorm_requested}), encoding="utf-8")


def _fake_best_effort(**_kwargs: object) -> None:
    return None


def test_phase_driver_read_result_env_filters_allowlist_and_cr(tmp_path: Path) -> None:
    env = tmp_path / "result.env"
    env.write_bytes(
        b"INIT_STATUS=ok\n"
        b"SECRET=drop\n"
        b"RUN_PARAMS_PATH=/tmp/run.json\n"
        b"OOS_SKIP_BREADCRUMB=skip\n"
        b"SETTLE_NEXT_ACTION=gate-b-continue\n"
        b"BAD=has\r\n"
    )  # pyright: ignore[reportUnusedCallResult]
    assert phase_driver_read_result_env(
        path=env,
        allow_keys=["INIT_STATUS", "RUN_PARAMS_PATH", "OOS_SKIP_BREADCRUMB", "SETTLE_NEXT_ACTION", "BAD"],
    ) == [
        ("INIT_STATUS", "ok"),
        ("RUN_PARAMS_PATH", "/tmp/run.json"),
        ("OOS_SKIP_BREADCRUMB", "skip"),
        ("SETTLE_NEXT_ACTION", "gate-b-continue"),
    ]


def test_phase_driver_read_result_env_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    target.write_text("INIT_STATUS=ok\n", encoding="utf-8")  # pyright: ignore[reportUnusedCallResult]
    link = tmp_path / "link.env"
    link.symlink_to(target)
    with pytest.raises(OSError, match="not a regular file"):
        phase_driver_read_result_env(path=link, allow_keys=["INIT_STATUS"])  # pyright: ignore[reportUnusedCallResult]


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
    assert load_bash_quoted_env(path=cache, allow_keys=["POSITIONAL_VALUE"])["POSITIONAL_VALUE"] == "hello world"


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
    design_lifecycle.write_bash_quoted_env(path=cache, data={"POSITIONAL_VALUE": value, "POSITIONAL_KIND": "verbal"})
    loaded = load_bash_quoted_env(path=cache, allow_keys=["POSITIONAL_VALUE"])
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
    state = design_lifecycle.relay_degraded_tools_gate_stdout(stdout=stdout, design_tmpdir=design)
    assert state["BOTH_DOWN_SEEN"] == "true"
    assert state["STEP0_STATUS"] == "needs-degraded-decision"


def test_relay_degraded_tools_gate_stdout_degraded_one_down_with_prompt(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".degraded-tools-gate-prompted").write_text("", encoding="utf-8")
    stdout = "DEGRADED=true\nBOTH_DOWN=false\n"
    state = design_lifecycle.relay_degraded_tools_gate_stdout(stdout=stdout, design_tmpdir=design)
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
        logging_util.emit_kv(key="CAPTURED", value="true")
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


def test_step_final_summary_core_emits_markers_and_cleans_bg_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary without newline", encoding="utf-8")

    def fake_render(argv: list[str]) -> int:
        assert "--post-publish-only" in argv
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step_final_summary_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" in contract
    assert "summary without newline\nLARCH_FINAL_SUMMARY_END" in contract
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

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        if cmd[2:4] == ["design", "route"]:
            (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            _write_ok_init_result(design, brainstorm_requested=True)
            return subprocess.CompletedProcess(cmd, 0, "INIT_STATUS=ok\nRENAMED=false\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
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

    def fake_append(
        *,
        plugin_root: Path,
        design_tmpdir: Path,
        site: str,
        tool: str,
        exit_code: int | str,
        category: str,
        output_file: Path,
    ) -> bool:
        _ = plugin_root, site, output_file
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

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[2:4] == ["design", "route"]:
            (design / ".design-route-result.env").write_text("ROUTE=proceed\nBRAINSTORM_PREFIX=true\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\nBRAINSTORM_PREFIX=true\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            assert "--brainstorm-requested" in cmd
            assert cmd[cmd.index("--brainstorm-requested") + 1] == "true"
            _write_ok_init_result(design, brainstorm_requested=True)
            return subprocess.CompletedProcess(cmd, 0, "INIT_STATUS=ok\nRENAMED=false\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    rc = design_lifecycle.step0_route_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--plugin-root", str(CLI.parent.parent)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "auto-enabling brainstorm mode" in captured.out
    state = (design / ".design-step0-route-state.env").read_text(encoding="utf-8")
    assert "brainstorm_requested=true" in state
    run_params = json.loads((design / "run-params.json").read_text(encoding="utf-8"))
    assert run_params["brainstorm_requested"] is True



def test_step0_route_proceed_folds_init_after_route_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")
    calls: list[str] = []
    stdout = StringIO()

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[2:4] == ["design", "route"]:
            calls.append("route")
            (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            calls.append("init")
            assert (design / ".design-step0-route-state.env").is_file()
            assert "ROUTE=proceed" not in stdout.getvalue()
            _write_ok_init_result(design)
            return subprocess.CompletedProcess(cmd, 0, "INIT_STATUS=ok\nRENAMED=false\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)
    with redirect_stdout(stdout):
        rc = design_lifecycle.step0_route_main(_step0_wrapper_args(env_path))

    assert rc == 0
    assert calls == ["route", "init"]
    assert (design / "feature-description.txt").read_text(encoding="utf-8") == "# Title\n\nbody"
    assert (design / "run-params.json").is_file()
    out = stdout.getvalue()
    assert "ROUTE=proceed" in out
    assert "INIT_STATUS=ok" in out
    assert out.index("ROUTE=proceed") < out.index("INIT_STATUS=ok")


@pytest.mark.parametrize("route", ["clarify", "already-planned", "resume@2a"])
def test_step0_route_non_proceed_routes_do_not_init(route: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")
    init_called = False

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal init_called
        if cmd[2:4] == ["design", "route"]:
            (design / ".design-route-result.env").write_text(f"ROUTE={route}\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, f"ROUTE={route}\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            init_called = True
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    rc = design_lifecycle.step0_route_main(_step0_wrapper_args(env_path))
    assert rc == 0
    assert not init_called
    assert f"ROUTE={route}" in capsys.readouterr().out
    assert not (design / "feature-description.txt").exists()


def test_step0_route_proceed_init_failure_keeps_state_and_hides_route(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[2:4] == ["design", "route"]:
            (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            assert (design / ".design-step0-route-state.env").is_file()
            (design / ".design-init-runparams-result.env").write_text("INIT_STATUS=env-refresh-failed\nRUN_PARAMS_PATH=\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 1, "", "design-init-runparams.sh: failed\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    rc = design_lifecycle.step0_route_main(_step0_wrapper_args(env_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert (design / ".design-step0-route-state.env").is_file()
    assert "ROUTE=proceed" not in captured.out
    assert "design-init-runparams.sh failed" in captured.err


def test_step0_route_proceed_pre_init_pause_hides_route_and_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")
    init_called = False

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal init_called
        if cmd[2:4] == ["design", "route"]:
            (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
            (design / ".pause-requested").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            init_called = True
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def fake_pause(_argv: list[str]) -> int:
        print("PAUSE_OK=true")
        return 5

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    monkeypatch.setattr(design_lifecycle, "_read_json_issue", _fake_read_json_issue_title)

    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step0_route_main(_step0_wrapper_args(env_path))
    captured = capsys.readouterr()
    assert exc.value.code == 5
    assert not init_called
    assert "PAUSE_OK=true" in captured.out
    assert "ROUTE=proceed" not in captured.out
    assert "INIT_STATUS=" not in captured.out
    assert (design / ".design-step0-route-state.env").is_file()


def test_step0_route_emits_resume_step_kvs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="owner/repo")
    invoked: list[list[str]] = []

    def fake_route(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        invoked.append(list(cmd))
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
    assert not any(cmd[2:4] == ["design", "step2a"] for cmd in invoked if len(cmd) >= 4)


def test_step0_route_preserves_pre_set_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".design-step0-parsed.env").write_text("POSITIONAL_KIND=issue\nPOSITIONAL_VALUE=42\n", encoding="utf-8")
    (design / "issue-body.txt").write_text("body\n", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch, ISSUE_NUMBER="42", ISSUE_TITLE="Title", HAS_CLARIFY_LABEL="false", REPO="preset/repo")
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        if cmd[2:4] == ["design", "route"]:
            (design / ".design-route-result.env").write_text("ROUTE=proceed\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "ROUTE=proceed\n", "")
        if cmd[2:4] == ["design", "init-runparams"]:
            _write_ok_init_result(design)
            return subprocess.CompletedProcess(cmd, 0, "INIT_STATUS=ok\nRENAMED=false\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
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
    state = design_lifecycle.relay_degraded_tools_gate_stdout(stdout=stdout, design_tmpdir=design)
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



def test_step1d5_entry_disabled_skip_writes_completion_and_directives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "run-params.json").write_text(json.dumps({"brainstorm_requested": False}), encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    monkeypatch.setattr(design_lifecycle, "_run_best_effort", _fake_best_effort)

    assert design_lifecycle.step1d5_main([*_step0_wrapper_args(env_path), "--mode", "entry"]) == 0
    completed = design / ".completed"
    for name in ("step-1c", "step-1d", "step-1d.5"):
        assert (completed / name).is_file()
    captured = capsys.readouterr()
    assert "STEP1D5_ACTION=skip" in captured.out
    assert "STEP1D5_SKIP_KIND=disabled" in captured.out


def test_step1d5_entry_already_complete_precedes_disabled_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "run-params.json").write_text(json.dumps({"brainstorm_requested": False}), encoding="utf-8")
    (design / ".brainstorm-done").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    monkeypatch.setattr(design_lifecycle, "_run_best_effort", _fake_best_effort)

    assert design_lifecycle.step1d5_main([*_step0_wrapper_args(env_path), "--mode", "entry"]) == 0
    assert (design / ".completed" / "step-1d.5").is_file()
    captured = capsys.readouterr()
    assert "STEP1D5_ACTION=skip" in captured.out
    assert "STEP1D5_SKIP_KIND=already-complete" in captured.out
    assert "STEP1D5_SKIP_KIND=disabled" not in captured.out


def test_step1d5_entry_requested_with_done_skips_already_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "run-params.json").write_text(json.dumps({"brainstorm_requested": True}), encoding="utf-8")
    (design / ".brainstorm-done").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    monkeypatch.setattr(design_lifecycle, "_run_best_effort", _fake_best_effort)

    assert design_lifecycle.step1d5_main([*_step0_wrapper_args(env_path), "--mode", "entry"]) == 0
    assert "STEP1D5_SKIP_KIND=already-complete" in capsys.readouterr().out


def test_step1d5_entry_requested_without_done_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "run-params.json").write_text(json.dumps({"brainstorm_requested": True}), encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)
    monkeypatch.setattr(design_lifecycle, "_run_best_effort", _fake_best_effort)

    assert design_lifecycle.step1d5_main([*_step0_wrapper_args(env_path), "--mode", "entry"]) == 0
    assert not (design / ".completed" / "step-1d.5").exists()
    captured = capsys.readouterr()
    assert "STEP1D5_ACTION=run" in captured.out
    assert "STEP1D5_SKIP_KIND=" not in captured.out


def test_step1d5_entry_disabled_pause_hides_directives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "run-params.json").write_text(json.dumps({"brainstorm_requested": False}), encoding="utf-8")
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_pause(_argv: list[str]) -> int:
        assert (design / ".completed" / "step-1d.5").is_file()
        print("PAUSE_OK=true")
        return 4

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    with pytest.raises(SystemExit) as exc:
        design_lifecycle.step1d5_main([*_step0_wrapper_args(env_path), "--mode", "entry"])
    captured = capsys.readouterr()
    assert exc.value.code == 4
    assert "PAUSE_OK=true" in captured.out
    assert "STEP1D5_ACTION=" not in captured.out

def test_step1d5_entry_writes_sentinels_before_pause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = _write_session_env(tmp_path, design, monkeypatch)

    def fake_pause(_argv: list[str]) -> int:
        completed = design / ".completed"
        for name in ("step-1c", "step-1d", "step-1d.5"):
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
    design_lifecycle.write_bash_quoted_env(path=cache, data={"POSITIONAL_VALUE": value, "POSITIONAL_KIND": "verbal"})
    loaded = load_bash_quoted_env(path=cache, allow_keys=["POSITIONAL_VALUE"])
    assert loaded["POSITIONAL_VALUE"] == value


def test_step2a_repairs_sentinels_without_plugin_root(tmp_path: Path) -> None:
    (tmp_path / "run-params.json").write_text('{"brainstorm_requested": false}\n', encoding="utf-8")
    assert design_lifecycle._folded_step2a_sentinel_prep(tmp_path) == 0  # pyright: ignore[reportPrivateUsage]
    assert (tmp_path / "approach-synthesis.txt").read_text(encoding="utf-8") == "NO_SKETCHES\n"
    assert (tmp_path / "contested-decisions.md").read_text(encoding="utf-8") == "NO_CONTESTED_DECISIONS\n"
    assert (tmp_path / "dialectic-resolutions.md").read_text(encoding="utf-8") == ""
    assert (tmp_path / ".completed" / "step-2a").is_file()
    assert (tmp_path / ".completed" / "step-1d.5").is_file()


def test_step2a_skips_step1d5_when_brainstorm_requested(tmp_path: Path) -> None:
    (tmp_path / "run-params.json").write_text('{"brainstorm_requested": true}\n', encoding="utf-8")
    assert design_lifecycle._folded_step2a_sentinel_prep(tmp_path) == 0  # pyright: ignore[reportPrivateUsage]
    assert not (tmp_path / ".completed" / "step-1d.5").exists()


def test_step2a_refuses_conflicting_sentinel_artifacts(tmp_path: Path) -> None:
    (tmp_path / "approach-synthesis.txt").write_text("real sketch\n", encoding="utf-8")
    assert design_lifecycle._folded_step2a_sentinel_prep(tmp_path) == 1  # pyright: ignore[reportPrivateUsage]


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


def test_postplan_decide_ok_returns_rows_and_touches(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=0,
        captured_stdout="POSTPLAN_EMIT_STATUS=ok\n",
        validate={},
        plan_source="",
        fallback_used="false",
        dirty_recovery=False,
        plan_summary_exists=False,
    )

    assert decision.rows == ("POSTPLAN_RC=0\n", "POSTPLAN_STATUS=ok\n")
    assert decision.touches == (paths.step2b5_done, paths.step2b_done)
    assert not decision.writes
    assert not decision.unlinks


def test_postplan_decide_inline_retry_returns_apply_metadata(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=10,
        captured_stdout="POSTPLAN_EMIT_STATUS=ok\n",
        validate={"VALIDATE_STATUS": "defects-found", "VALIDATE_DEFECT_COUNT": "1"},
        plan_source="drafter",
        fallback_used="false",
        dirty_recovery=False,
        plan_summary_exists=True,
    )

    assert decision.clear_scout_manifests is True
    assert "SCOUT_STALE_CLEARED=true\n" in decision.rows
    assert decision.touches == (paths.inline_retry_done, paths.inline_retry_pending)
    assert decision.writes == ((paths.fallback_used, "true\n"), (paths.plan_source, "inline\n"))
    assert decision.unlinks == (paths.plan_summary,)


def test_postplan_decide_fallback_used_skips_inline_retry(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=10,
        captured_stdout="",
        validate={},
        plan_source="drafter",
        fallback_used="true",
        dirty_recovery=False,
        plan_summary_exists=True,
    )

    assert decision.clear_scout_manifests is False
    assert all("SCOUT_STALE_CLEARED" not in row for row in decision.rows)
    assert not decision.touches
    assert not decision.writes
    assert not decision.unlinks


def test_postplan_decide_rc_11_sets_post_emit_pause_metadata(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=11,
        captured_stdout="POSTPLAN_EMIT_STATUS=ok\n",
        validate={},
        plan_source="",
        fallback_used="false",
        dirty_recovery=False,
        plan_summary_exists=False,
    )

    assert decision.rows == ("POSTPLAN_RC=11\n", "POSTPLAN_STATUS=pause-save\n")
    assert decision.pause_save is True
    assert decision.print_stdout_before_system_exit is False
    assert not decision.touches


def test_postplan_decide_rc_12_returns_rows_and_touches(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=12,
        captured_stdout="POSTPLAN_EMIT_STATUS=ok\n",
        validate={},
        plan_source="",
        fallback_used="false",
        dirty_recovery=False,
        plan_summary_exists=False,
    )

    assert decision.rows == ("POSTPLAN_RC=12\n", "POSTPLAN_STATUS=plan-size-trigger\n")
    assert decision.touches == (paths.step2b_done,)


def test_postplan_decide_rc_13_returns_rows_and_touches(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=13,
        captured_stdout="POSTPLAN_EMIT_STATUS=ok\n",
        validate={},
        plan_source="",
        fallback_used="false",
        dirty_recovery=False,
        plan_summary_exists=False,
    )

    assert decision.rows == ("POSTPLAN_RC=13\n", "POSTPLAN_STATUS=partition-requested\n")
    assert decision.touches == (paths.step2b_done,)


def test_postplan_decide_fatal_rc_sets_print_captured_metadata(tmp_path: Path) -> None:
    paths = design_lifecycle.PostplanPaths.from_design_tmpdir(tmp_path)
    decision = design_lifecycle._postplan_decide(  # pyright: ignore[reportPrivateUsage]
        paths=paths,
        site="step2b",
        rc=2,
        captured_stdout="POSTPLAN_EMIT_STATUS=ok\n",
        validate={},
        plan_source="",
        fallback_used="false",
        dirty_recovery=False,
        plan_summary_exists=False,
    )

    assert decision.print_captured_before_return is True
    assert "configuration error" in decision.fatal_stderr
    assert not decision.rows


def test_postplan_executor_pre_emit_pause_skips_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".pause-requested").write_text("", encoding="utf-8")
    called = False

    def fake_emit(_argv: list[str]) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    result = design_lifecycle._shared_step2b_postplan_body(  # pyright: ignore[reportPrivateUsage]
        parsed=design_lifecycle.WrapperArgs(site="step2b"),
        design_tmpdir=tmp_path,
    )
    assert result.postplan_rc == 11
    assert result.stdout_lines == "POSTPLAN_RC=11\nPOSTPLAN_STATUS=pause-save\n"
    assert called is False


def test_postplan_executor_gate_b_clears_scout_before_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scout = tmp_path / "scout-plan-manifest.json"
    scout.write_text("{}\n", encoding="utf-8")
    seen: list[str] = []

    def fake_emit(argv: list[str]) -> int:
        seen.extend(argv)
        assert not scout.is_file()
        print("POSTPLAN_EMIT_STATUS=ok")
        return 0

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    result = design_lifecycle._shared_step2b_postplan_body(  # pyright: ignore[reportPrivateUsage]
        parsed=design_lifecycle.WrapperArgs(site="gate-b"),
        design_tmpdir=tmp_path,
    )

    assert result.stdout_lines == "POSTPLAN_EMIT_STATUS=ok\nPOSTPLAN_RC=0\nPOSTPLAN_STATUS=ok\n"
    assert "--snapshot-original" not in seen


@pytest.mark.parametrize(
    ("emit_rc", "expected_stdout", "expected_touch"),
    [
        (0, "POSTPLAN_EMIT_STATUS=ok\nPOSTPLAN_RC=0\nPOSTPLAN_STATUS=ok\n", "step-2b.5"),
        (12, "POSTPLAN_EMIT_STATUS=ok\nPOSTPLAN_RC=12\nPOSTPLAN_STATUS=plan-size-trigger\n", "step-2b"),
        (13, "POSTPLAN_EMIT_STATUS=ok\nPOSTPLAN_RC=13\nPOSTPLAN_STATUS=partition-requested\n", "step-2b"),
    ],
)
def test_postplan_executor_stdout_lines_golden_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    emit_rc: int,
    expected_stdout: str,
    expected_touch: str,
) -> None:
    def fake_emit(_argv: list[str]) -> int:
        print("POSTPLAN_EMIT_STATUS=ok")
        return emit_rc

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    result = design_lifecycle._shared_step2b_postplan_body(  # pyright: ignore[reportPrivateUsage]
        parsed=design_lifecycle.WrapperArgs(site="step2b"),
        design_tmpdir=tmp_path,
    )

    assert result.stdout_lines == expected_stdout
    assert (tmp_path / ".completed" / expected_touch).is_file()


def test_postplan_executor_rc_10_inline_retry_stdout_lines_golden(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".step2b-plan-source").write_text("drafter\n", encoding="utf-8")

    def fake_emit(_argv: list[str]) -> int:
        (tmp_path / ".design-postplan-emit-result.env").write_text(
            "VALIDATE_STATUS=defects-found\nVALIDATE_DEFECT_COUNT=1\n",
            encoding="utf-8",
        )
        print("POSTPLAN_EMIT_STATUS=ok")
        return 10

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    result = design_lifecycle._shared_step2b_postplan_body(  # pyright: ignore[reportPrivateUsage]
        parsed=design_lifecycle.WrapperArgs(site="step2b"),
        design_tmpdir=tmp_path,
    )

    assert result.stdout_lines == (
        "POSTPLAN_EMIT_STATUS=ok\n"
        "POSTPLAN_RC=10\n"
        "POSTPLAN_STATUS=validate-failed\n"
        "SCOUT_STALE_CLEARED=true\n"
        "**⚠ 2b: drafter plan failed postplan validation — re-entering inline drafting once**\n"
        "VALIDATE_STATUS=defects-found\n"
        "VALIDATE_DEFECT_COUNT=1\n"
    )


def test_postplan_executor_rc_11_prints_full_buffer_before_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_emit(_argv: list[str]) -> int:
        print("POSTPLAN_EMIT_STATUS=ok")
        return 11

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    result = design_lifecycle._shared_step2b_postplan_body(  # pyright: ignore[reportPrivateUsage]
        parsed=design_lifecycle.WrapperArgs(site="step2b"),
        design_tmpdir=tmp_path,
    )
    out = capsys.readouterr().out
    assert out == ""
    assert result.postplan_rc == 11
    assert result.stdout_lines == (
        "POSTPLAN_EMIT_STATUS=ok\n"
        "POSTPLAN_RC=11\n"
        "POSTPLAN_STATUS=pause-save\n"
    )


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


def test_step2b5_self_logs_on_rc2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_check(_argv: list[str]) -> int:
        print("PLAN_SIZE_STATUS=missing-diff-lines")
        return 2

    monkeypatch.setattr(design_lifecycle.plan_quality, "check_plan_size_main", fake_check)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b5_main([])
    out = capsys.readouterr().out
    assert rc == 2
    assert "PLAN_SIZE_STATUS=missing-diff-lines" in out
    validation_log = tmp_path / "check-plan-size.validation.log"
    assert validation_log.read_text(encoding="utf-8") == "PLAN_SIZE_STATUS=missing-diff-lines\n"
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step 2b.5" in issues
    assert "python/cli.py plan check-size" in issues


def test_step2b5_self_logs_on_rc3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(_argv: list[str]) -> int:
        print("usage: missing plan", file=sys.stderr)
        return 3

    monkeypatch.setattr(design_lifecycle.plan_quality, "check_plan_size_main", fake_check)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b5_main([])
    assert rc == 3
    validation_log = tmp_path / "check-plan-size.validation.log"
    assert validation_log.read_text(encoding="utf-8") == "usage: missing plan\n"
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step 2b.5" in issues
    assert "python/cli.py plan check-size" in issues


def test_step2b5_no_log_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_check(_argv: list[str]) -> int:
        print("PLAN_SIZE_STATUS=ok")
        return 0

    monkeypatch.setattr(design_lifecycle.plan_quality, "check_plan_size_main", fake_check)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b5_main([])
    assert rc == 0
    assert not (tmp_path / "check-plan-size.validation.log").exists()
    assert not (tmp_path / "execution-issues.md").exists()


def test_step2_launcher_argv_rehydrates_wrapper_env(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(
        f"export DESIGN_TMPDIR={str(design)!r}\nexport ISSUE_NUMBER='42'\n",
        encoding="utf-8",
    )
    parsed = design_lifecycle._parse_common_wrapper_args(["--session-env-path", str(session_env), "--claude-pid", "123"])  # pyright: ignore[reportPrivateUsage]
    design_lifecycle._rehydrate_wrapper_env(parsed)  # pyright: ignore[reportPrivateUsage]
    rc = design_lifecycle._folded_step2a_sentinel_prep(design)  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert os.environ["DESIGN_TMPDIR"] == str(design)
    assert os.environ["ISSUE_NUMBER"] == "42"


def test_step2a_rejects_missing_design_tmpdir(tmp_path: Path) -> None:
    session_env = tmp_path / "session-env.sh"
    session_env.write_text(f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}\n", encoding="utf-8")
    assert design_lifecycle.step2b_drafter_main(["--session-env-path", str(session_env), "--claude-pid", "123"]) == 1


def test_step2a_rejects_relative_design_tmpdir(tmp_path: Path) -> None:
    session_env = tmp_path / "session-env.sh"
    session_env.write_text("export DESIGN_TMPDIR=relative/path\n", encoding="utf-8")
    assert design_lifecycle.step2b_drafter_main(["--session-env-path", str(session_env), "--claude-pid", "123"]) == 2


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
    assert design_lifecycle._folded_step2a_sentinel_prep(tmp_path) == 0  # pyright: ignore[reportPrivateUsage]
    assert (tmp_path / "approach-synthesis.txt").read_text(encoding="utf-8") == "NO_SKETCHES\n"


@pytest.mark.parametrize(
    ("pause_stdout", "expected_rc", "expect_action"),
    [
        ("PAUSE_OK=true\n", 0, True),
        ("PAUSE_OK=false\n", 1, False),
    ],
)
def test_step2b_drafter_pause_before_fallback_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pause_stdout: str,
    expected_rc: int,
    expect_action: bool,
) -> None:
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

    def fake_pause(**_kw: object) -> int:
        print(pause_stdout, end="")
        return 0

    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)
    rc = design_lifecycle.step2b_drafter_main([])
    out = capsys.readouterr().out
    assert rc == expected_rc
    assert pause_stdout.strip() in out
    assert ("DRAFTER_NEXT_ACTION=pause-terminal" in out) is expect_action
    if not expect_action:
        assert "STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1" not in out
    assert "POSTPLAN_RC=11" not in out
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

    def fake_postplan(
        *,
        parsed: design_lifecycle.WrapperArgs,
        design_tmpdir: Path,
        ctx: object | None = None,
        defer_pause_save: bool = False,
    ) -> design_lifecycle.PostplanResult:
        _ = parsed, design_tmpdir, ctx, defer_pause_save
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
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", lambda **_kw: 11)  # type: ignore[arg-type]
    rc = design_lifecycle.step2b5_main([])
    assert rc == 11
    assert called is False


def test_step2b_postplan_rc_11_returns_pause_save_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))

    def fake_pause(**_kw: object) -> int:
        print("PAUSE_OK=true")
        return 0

    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("POSTPLAN_RC=11") == 1
    assert "PAUSE_OK=true" in out


def test_step2b_postplan_rc_11_pause_save_gates_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_emit(_argv: list[str]) -> int:
        print("POSTPLAN_EMIT_STATUS=ok")
        return 11

    def fake_pause(**_kw: object) -> int:
        print("PAUSE_OK=false")
        return 0

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    out = capsys.readouterr().out
    assert rc == 1
    assert out.count("POSTPLAN_RC=11") == 1
    assert "PAUSE_OK=false" in out


def test_step2b_postplan_rc_11_pause_save_succeeds_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_emit(_argv: list[str]) -> int:
        print("POSTPLAN_EMIT_STATUS=ok")
        return 11

    def fake_pause(**_kw: object) -> int:
        print("PAUSE_OK=true")
        return 0

    monkeypatch.setattr(design_lifecycle.design_postplan, "postplan_emit_main", fake_emit)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rc = design_lifecycle.step2b_postplan_main(["--site", "step2b"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("POSTPLAN_RC=11") == 1
    assert "PAUSE_OK=true" in out


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
                return real_run_stall(callable_obj=callable_obj, argv=argv, stdout_path=stdout_path, stderr_path=stderr_path)
            if callable_obj is stall_recovery.init_attempts_main:
                return 0
            if callable_obj is stall_recovery.classify_main and stdout_path is not None:
                stdout_path.write_text("", encoding="utf-8")
                return 0
            return real_run_stall(callable_obj=callable_obj, argv=argv, stdout_path=stdout_path, stderr_path=stderr_path)

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
        logging_util.emit_kv(key="CAPTURED", value="true")
        return 0

    assert design_lifecycle.capture_contract_stream_to_paths(emit_contract, out, err) == 0
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        logging_util.quiet_init(argv0="parent-quiet")
        logging_util.emit_kv(key="POST_CAPTURE", value="ok")
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
            return real_run_stall(callable_obj=callable_obj, argv=argv, stdout_path=stdout_path, stderr_path=stderr_path)
        if callable_obj is stall_recovery.init_attempts_main:
            return 0
        if callable_obj is stall_recovery.classify_main and stdout_path is not None:
            stdout_path.write_text("", encoding="utf-8")
            return 0
        return real_run_stall(callable_obj=callable_obj, argv=argv, stdout_path=stdout_path, stderr_path=stderr_path)

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
            return real_run_stall(callable_obj=callable_obj, argv=argv, stdout_path=stdout_path, stderr_path=stderr_path)
        if callable_obj is stall_recovery.init_attempts_main:
            return 0
        if callable_obj is stall_recovery.classify_main and stdout_path is not None:
            stdout_path.write_text("", encoding="utf-8")
            return 0
        return real_run_stall(callable_obj=callable_obj, argv=argv, stdout_path=stdout_path, stderr_path=stderr_path)

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


def test_step_final_summary_render_exception_skips_sentinel_and_marked_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def boom(_argv: list[str]) -> int:
        raise RuntimeError("render broke")

    monkeypatch.setattr(design_summary, "render_final_summary_main", boom)
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step_final_summary_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 1
    assert not (tmp_path / ".completed" / "step-final-summary").is_file()
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract


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
    def capture_marker(*, design_tmpdir: object, step: str, claude_pid: str = ""):
        _ = design_tmpdir, step
        seen.append(claude_pid)
        yield

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_ok(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(design_lifecycle, "_bg_wait_marker_context", capture_marker)
    monkeypatch.setattr(design_summary, "render_final_summary_main", render_ok)
    design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "789", "--outcome", "approved"])
    assert seen == ["789"]


def test_step_final_summary_emits_report_gate_sidecars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")
    (tmp_path / "design-failure-chat-print.md").write_text("chat sidecar\n", encoding="utf-8")

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_ok_sidecar(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(design_summary, "render_final_summary_main", render_ok_sidecar)
    _, contract, _ = _capture_core_contract(
        design_lifecycle.step_final_summary_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"],
        tmp_path,
        monkeypatch,
    )
    handoff = tmp_path / "design-report-gate-sidecars.md"
    assert handoff.is_file()
    assert "REPORT_GATE_SIDECARS_FILE=" in contract
    assert str(handoff) in contract


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


def _capture_core_contract(
    core_fn: Callable[..., tuple[int, list[str]]],
    argv: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, str, str]:
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    logging_util.reset_quiet_state()
    out = tmp_path / "contract.stdout.log"
    err = tmp_path / "contract.stderr.log"
    rc = design_lifecycle.capture_contract_stream_to_paths(core_fn, out, err, argv)
    logging_util.reset_quiet_state()
    return rc, out.read_text(encoding="utf-8"), err.read_text(encoding="utf-8")


def _setup_step5c_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: str) -> tuple[Path, Path]:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
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


def test_step5c_core_render_uses_ctx_snapshot_when_ambient_env_overrides_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", SESSION_ID="run-1", REPO="owner/repo")
    real_rehydrate = design_lifecycle._rehydrate_wrapper_env  # pyright: ignore[reportPrivateUsage]

    def rehydrate_then_ambient_override(parsed: object) -> dict[str, str]:
        env = real_rehydrate(parsed)  # type: ignore[arg-type]
        os.environ["ISSUE_NUMBER"] = "999"
        os.environ["SESSION_ID"] = "ambient-session"
        os.environ["REPO"] = "ambient/repo"
        return env

    monkeypatch.setattr(design_lifecycle, "_rehydrate_wrapper_env", rehydrate_then_ambient_override)
    seen_argv: list[list[str]] = []

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(argv: list[str]) -> int:
        seen_argv.append(list(argv))
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert seen_argv == [
        [
            "--outcome",
            "approved",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(design),
            "--issue-number",
            "42",
            "--session-id",
            "run-1",
            "--post-publish-only",
            "--repo",
            "owner/repo",
        ]
    ]


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



def test_step5c_core_requires_step5b5_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
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
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")

    def fake_pause(_argv: list[str]) -> int:
        logging_util.emit_kv(key="PAUSE_OK", value="true")
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "STEP5C_STATUS=pause-save" in contract
    assert "PAUSE_OK=true" in contract
    assert not (design / ".completed" / "step-5c-terminal").exists()


def test_step5c_core_assembles_publish_argv_and_cleans_bg_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "777", "--skip-validate"],
        tmp_path,
        monkeypatch,
    )
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
    assert "PUBLISH_RC=0" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN\nsummary body\nLARCH_FINAL_SUMMARY_END" in contract
    assert "unmarked render stdout" not in contract
    assert "unmarked render stdout" in (design / "render-final-summary.approved.stdout.log").read_text(encoding="utf-8")


def test_step5c_core_rc1_uses_stdout_over_stale_primary_and_binds_final_summary_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    stale = design / ".design-publish-result.env"
    stale.write_text("PLAN_WRITE_OK=true\nFINAL_SUMMARY_PATH=/stale/final-summary.md\nPUBLISH_OK=true\n", encoding="utf-8")
    current_summary = design / "current-summary.md"
    seen_env: list[str] = []
    seen_argv: list[list[str]] = []

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design, plan_write_ok="false", publish_ok="", final_summary=current_summary), end="")
        current_summary.write_text("current failed summary\n", encoding="utf-8")
        return 1

    def fake_render(_argv: list[str]) -> int:
        seen_argv.append(list(_argv))
        seen_env.append(os.environ.get("FINAL_SUMMARY_PATH", ""))
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert seen_env == [""]
    assert seen_argv == [
        [
            "--outcome",
            "failed-plan-write",
            "--mode",
            "N/A",
            "--design-tmpdir",
            str(design),
            "--issue-number",
            "42",
            "--session-id",
            "run-1",
            "--post-publish-only",
        ]
    ]
    status = (design / ".design-step5c-status.env").read_text(encoding="utf-8")
    assert "PLAN_WRITE_OK=false" in status
    assert "PUBLISH_STDOUT_FALLBACK=true" in status
    assert "CLEANUP_ELIGIBLE=false" in status
    assert not (design / ".completed" / "step-5c").exists()
    assert "current failed summary" in contract


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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "STEP5C_STATUS=validator-defects" in contract
    assert "REPORT_GATE_SIDECARS_FILE=" in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract
    assert "PLAN_WRITE_OK=false" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_auto_compose_basic(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    plan = design / "plan.txt"
    plan.write_text(
        "## Approach\n\nDo the thing.\n\n## Testing strategy\n\nRun tests.\n\ndiff_lines: 5\n",
        encoding="utf-8",
    )
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "## Plan" in composed
    assert "Do the thing." in composed
    assert "## Acceptance" in composed
    assert "Run tests." in composed
    assert "diff_lines: 5" in composed


def test_step5c_auto_compose_noop_when_file_exists(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    existing = "## Plan\n\nexisting content\n\ndiff_lines: 1\n"
    (design / "composed-plan.md").write_text(existing, encoding="utf-8")
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    assert (design / "composed-plan.md").read_text(encoding="utf-8") == existing


def test_step5c_auto_compose_fallback_acceptance_when_no_testing_strategy(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text("## Approach\n\nBody.\n\ndiff_lines: 3\n", encoding="utf-8")
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "## Acceptance" in composed
    assert "See Testing strategy in plan." in composed


def test_step5c_auto_compose_no_plan_txt_emits_warning(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    assert not (design / "composed-plan.md").exists()


def test_step5c_auto_compose_strips_leading_plan_header(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        "## Plan\n\n## Approach\n\nDo the thing.\n\n## Testing strategy\n\nRun tests.\n\ndiff_lines: 5\n",
        encoding="utf-8",
    )
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert composed.count("## Plan") == 1
    assert "Do the thing." in composed
    assert "diff_lines: 5" in composed


def test_step5c_auto_compose_falls_back_to_diff_lines_sidecar(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text("## Approach\n\nBody without trailer.\n", encoding="utf-8")
    (design / "diff-lines.txt").write_text("42\n", encoding="utf-8")
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_lines: 42" in composed


def test_step5c_auto_compose_falls_back_to_diff_lines_with_optional_trailers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text("## Approach\n\nBody.\n", encoding="utf-8")
    (design / "diff-lines.txt").write_text("7\n", encoding="utf-8")
    (design / ".gate-b-optional-trailer-keys.values").write_text(
        "diff_added=10\ndiff_deleted=3\nmechanical_churn=false\n",
        encoding="utf-8",
    )
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_added: 10" in composed
    assert "diff_deleted: 3" in composed
    assert "mechanical_churn: false" in composed
    assert "diff_lines: 7" in composed


def test_step5c_auto_compose_peels_orphan_optional_trailers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        "## Approach\n\nBody.\n\ndiff_added: 10\ndiff_deleted: 3\nmechanical_churn: false\n",
        encoding="utf-8",
    )
    (design / "diff-lines.txt").write_text("7\n", encoding="utf-8")
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_added: 10" in composed
    assert "Body." in composed
    assert "diff_lines: 7" in composed


def test_step5c_auto_compose_preserves_optional_trailers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        "## Approach\n\nBody.\n\ndiff_added: 10\ndiff_deleted: 3\nmechanical_churn: false\ndiff_lines: 7\n",
        encoding="utf-8",
    )
    design_lifecycle._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "diff_added: 10" in composed
    assert "diff_deleted: 3" in composed
    assert "mechanical_churn: false" in composed
    assert "diff_lines: 7" in composed


def test_step5c_core_auto_composes_when_composed_plan_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    (design / "plan.txt").write_text(
        "## Approach\n\nFix the bug.\n\n## Testing strategy\n\nRun pytest.\n\ndiff_lines: 2\n",
        encoding="utf-8",
    )

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "777", "--skip-validate"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "## Plan" in composed
    assert "Fix the bug." in composed
    assert "## Acceptance" in composed
    assert "Run pytest." in composed
    assert "diff_lines: 2" in composed


def test_step5c_core_publish_tail_abort_stages_renders_and_writes_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 1
    assert (design / "design-failure-terminal-state.env").is_file()
    assert "FAILURE_OUTCOME=failed-publish-tail" in (design / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    stdout_log = design / "design-stage-terminal-state.stdout.log"
    stderr_log = design / "design-stage-terminal-state.stderr.log"
    assert stdout_log.is_file()
    assert stderr_log.is_file()
    assert stdout_log.stat().st_size > 0
    assert (design / ".completed" / "step-5c-terminal").is_file()
    assert "LARCH_FINAL_SUMMARY_BEGIN\nabort summary\nLARCH_FINAL_SUMMARY_END" in contract
    assert "REPORT_GATE_SIDECARS_FILE=" in contract


@pytest.mark.parametrize(
    ("session_id", "standalone_heavy_failed", "publish_ok", "expected_cleanup"),
    [
        ("", "false", "", "true"),
        ("run-abc", "false", "true", "true"),
        ("run-abc", "false", "false", "false"),
        ("run-abc", "false", "", "false"),
        ("run-abc", "true", "true", "false"),
    ],
)
def test_step5c_core_cleanup_eligibility_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_id: str,
    standalone_heavy_failed: str,
    publish_ok: str,
    expected_cleanup: str,
) -> None:
    design, env_path = _setup_step5c_design(
        tmp_path,
        monkeypatch,
        ISSUE_NUMBER="42",
        SESSION_ID=session_id,
        STANDALONE_HEAVY_FAILED=standalone_heavy_failed,
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


def test_step5c_core_empty_session_id_publish_success_is_cleanup_eligible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(
        tmp_path,
        monkeypatch,
        ISSUE_NUMBER="42",
        SESSION_ID="",
        STANDALONE_HEAVY_FAILED="false",
    )
    seen: list[list[str]] = []
    render_argv: list[list[str]] = []

    def fake_publish(argv: list[str]) -> int:
        seen.append(argv)
        print(_step5c_rows(design, publish_ok=""), end="")
        return 0

    def fake_render(argv: list[str]) -> int:
        render_argv.append(list(argv))
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert seen[0][seen[0].index("--session-id") : seen[0].index("--session-id") + 2] == ["--session-id", ""]
    assert render_argv
    assert "--session-id" not in render_argv[0]
    assert "CLEANUP_ELIGIBLE=true" in (design / ".design-step5c-status.env").read_text(encoding="utf-8")


def test_step5c_core_publish_tail_abort_rc5_stages_and_writes_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 1
    assert (design / "design-failure-terminal-state.env").is_file()
    stdout_log = design / "design-stage-terminal-state.stdout.log"
    stderr_log = design / "design-stage-terminal-state.stderr.log"
    assert stdout_log.is_file()
    assert stderr_log.is_file()
    assert stdout_log.stat().st_size > 0
    assert (design / ".completed" / "step-5c-terminal").is_file()
    assert "LARCH_FINAL_SUMMARY_BEGIN\nabort summary\nLARCH_FINAL_SUMMARY_END" in contract


def test_step5c_core_success_without_final_summary_skips_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract


def test_step5c_core_success_clears_bound_stale_summary_before_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    summary = design / "summaries" / "current-summary.md"
    summary.parent.mkdir()
    summary.write_text("stale success summary\n", encoding="utf-8")

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design, final_summary=summary), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        assert not summary.exists()
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert not summary.exists()
    assert "stale success summary" not in contract
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract


def test_step5c_core_render_failure_skips_stale_summary_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" not in contract


def test_step5c_core_captures_subprocess_stdout_from_publish_tail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    rc, contract, _ = _capture_core_contract(
        design_lifecycle.step5c_core,
        ["--session-env-path", str(env_path), "--claude-pid", "123"],
        tmp_path,
        monkeypatch,
    )
    assert rc == 0
    assert "PUBLISH_RC=0" in contract
    assert "WRITTEN=true" not in contract
    assert "MODE=write" not in contract


def test_step5c_core_restores_env_ipc_keys_after_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design, env_path = _setup_step5c_design(tmp_path, monkeypatch, ISSUE_NUMBER="42")
    before = {
        "FINAL_SUMMARY_PATH": os.environ.get("FINAL_SUMMARY_PATH"),
        "SUMMARY_OUTCOME": os.environ.get("SUMMARY_OUTCOME"),
    }

    def fake_publish(_argv: list[str]) -> int:
        print(_step5c_rows(design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    after = {
        "FINAL_SUMMARY_PATH": os.environ.get("FINAL_SUMMARY_PATH"),
        "SUMMARY_OUTCOME": os.environ.get("SUMMARY_OUTCOME"),
    }
    assert after == before


def test_step_final_summary_core_restores_env_ipc_keys_after_return(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary\n", encoding="utf-8")
    before = {
        "FINAL_SUMMARY_PATH": os.environ.get("FINAL_SUMMARY_PATH"),
        "SUMMARY_OUTCOME": os.environ.get("SUMMARY_OUTCOME"),
    }

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    def render_ok(_argv: list[str]) -> int:
        return 0

    monkeypatch.setattr(design_summary, "render_final_summary_main", render_ok)
    design_lifecycle.step_final_summary_core(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    after = {
        "FINAL_SUMMARY_PATH": os.environ.get("FINAL_SUMMARY_PATH"),
        "SUMMARY_OUTCOME": os.environ.get("SUMMARY_OUTCOME"),
    }
    assert after == before


def test_step5c_core_publish_design_tmpdir_matches_ctx_on_symlinked_session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_design = tmp_path / "real-design"
    (real_design / ".completed").mkdir(parents=True)
    (real_design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (real_design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    link_parent = tmp_path / "link-parent"
    link_parent.mkdir()
    symlink_design = link_parent / "design-link"
    symlink_design.symlink_to(real_design)
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(
        "\n".join(
            [
                f"export DESIGN_TMPDIR={symlink_design}",
                "export SESSION_ID=run-1",
                f"export CLAUDE_PLUGIN_ROOT={CLI.parent.parent}",
                "export ISSUE_NUMBER=42",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DESIGN_TMPDIR", str(symlink_design))
    seen: list[list[str]] = []

    def fake_publish(argv: list[str]) -> int:
        seen.append(argv)
        print(_step5c_rows(real_design), end="")
        return 0

    def fake_render(_argv: list[str]) -> int:
        (real_design / "final-summary.md").write_text("summary\n", encoding="utf-8")
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(design_publish, "publish_core", fake_publish)
    monkeypatch.setattr(design_summary, "render_final_summary_main", fake_render)
    rc, _ = design_lifecycle.step5c_core(["--session-env-path", str(env_path), "--claude-pid", "123"])
    assert rc == 0
    assert seen
    publish_tmpdir = seen[0][seen[0].index("--design-tmpdir") + 1]
    assert Path(publish_tmpdir).resolve() == real_design.resolve()


def test_step_final_summary_main_does_not_call_quiet_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    quiet_argv0s: list[str | None] = []

    def track_quiet_init(*, argv0: str | None = None) -> None:
        quiet_argv0s.append(argv0)

    def fake_core(_argv: list[str]) -> tuple[int, list[str]]:
        return 0, []

    monkeypatch.setattr(logging_util, "quiet_init", track_quiet_init)
    monkeypatch.setattr(design_lifecycle, "step_final_summary_core", fake_core)
    rc = design_lifecycle.step_final_summary_main(["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"])
    assert rc == 0
    assert not quiet_argv0s


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


def test_step_final_summary_main_machine_rows_visible_under_inherited_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = _write_session_env(tmp_path, tmp_path, monkeypatch, ISSUE_NUMBER="0", SUMMARY_OUTCOME="approved")
    (tmp_path / "final-summary.md").write_text("summary body\n", encoding="utf-8")

    def fake_render(argv: list[str]) -> int:
        assert "--post-publish-only" in argv
        return 0

    import design_summary  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

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
        rc = design_lifecycle.step_final_summary_main(
            ["--session-env-path", str(env_path), "--claude-pid", "123", "--outcome", "approved"],
        )
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 65536).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert rc == 0
    assert "LARCH_FINAL_SUMMARY_BEGIN" in contract
    assert "LARCH_FINAL_SUMMARY_END" in contract


def _write_step5c_status(
    design: Path,
    *,
    plan_write_ok: str = "true",
    publish_ok: str = "true",
    standalone_heavy_failed: str = "false",
    session_id: str = "",
    cleanup_eligible: str = "true",
) -> None:
    (design / ".design-step5c-status.env").write_text(
        "\n".join(
            [
                f"PLAN_WRITE_OK={plan_write_ok}",
                f"PUBLISH_OK={publish_ok}",
                f"STANDALONE_HEAVY_FAILED={standalone_heavy_failed}",
                f"SESSION_ID={session_id}",
                "PUBLISH_RC=0",
                "PUBLISH_STDOUT_FALLBACK=false",
                f"CLEANUP_ELIGIBLE={cleanup_eligible}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _step6_args(env_path: Path) -> list[str]:
    return ["--session-env-path", str(env_path), "--claude-pid", "123"]


def _step6_design(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: str) -> tuple[Path, Path]:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, monkeypatch, **extra)
    return design, env_path


def _step6_env_without_plugin_root(tmp_path: Path, design: Path, monkeypatch: pytest.MonkeyPatch | None = None, *, design_tmpdir: str | None = None, **extra: str) -> Path:
    raw_tmpdir = str(design.resolve()) if design_tmpdir is None else design_tmpdir
    if monkeypatch is not None:
        if raw_tmpdir:
            monkeypatch.setenv("DESIGN_TMPDIR", raw_tmpdir)
        else:
            monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    env_path = tmp_path / "source-env.sh"
    lines = [
        f"export DESIGN_TMPDIR={raw_tmpdir}",
        "export SESSION_ID=run-1",
    ]
    lines.extend(f"export {key}={value}" for key, value in extra.items())
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def test_step6_prelude_in_flight_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    (design / ".bg-wait-active").write_text("", encoding="utf-8")
    rc = design_lifecycle.step6_prelude_core(_step6_args(env_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert "appears still in-flight" in captured.err
    assert "STEP6_PRELUDE_STATUS=skipped" not in captured.out


def test_step6_cleanup_in_flight_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    (design / ".bg-wait-active").write_text("", encoding="utf-8")
    rc = design_lifecycle.step6_cleanup_core(_step6_args(env_path))
    captured = capsys.readouterr()
    assert rc == 1
    assert "appears still in-flight" in captured.err
    assert "CLEANUP_STATUS=preserved" not in captured.out


def test_step6_missing_sidecar_skips_without_plugin_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _step6_env_without_plugin_root(tmp_path, design, monkeypatch)

    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 0
    prelude = capsys.readouterr()
    assert "STEP6_PRELUDE_STATUS=skipped" in prelude.out
    assert "appears still in-flight" not in prelude.err

    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    cleanup = capsys.readouterr()
    assert "CLEANUP_STATUS=preserved" in cleanup.out
    assert "appears still in-flight" not in cleanup.err


def test_step6_sidecar_overrides_stale_bg_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    (design / ".bg-wait-active").write_text("", encoding="utf-8")
    _write_step5c_status(design, plan_write_ok="false")
    cleanup_calls = 0

    def fake_cleanup(_argv: list[str]) -> int:
        nonlocal cleanup_calls
        cleanup_calls += 1
        return 0

    monkeypatch.setattr(session_env, "cleanup_tmpdir_main", fake_cleanup)

    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 0
    prelude = capsys.readouterr()
    assert "STEP6_PRELUDE_STATUS=skipped" in prelude.out
    assert "appears still in-flight" not in prelude.err

    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    cleanup = capsys.readouterr()
    assert "CLEANUP_STATUS=preserved" in cleanup.out
    assert "plan write did not succeed" in cleanup.out
    assert "appears still in-flight" not in cleanup.err
    assert cleanup_calls == 0


def test_step6_pause_wins_over_in_flight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch, ISSUE_NUMBER="42", REPO="owner/repo")
    (design / ".pause-requested").write_text("", encoding="utf-8")
    (design / ".bg-wait-active").write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_pause(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 0
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    captured = capsys.readouterr()
    assert len(calls) == 2
    assert all(call == ["--design-tmpdir", str(design), "--issue", "42", "--repo", "owner/repo"] for call in calls)
    assert "appears still in-flight" not in captured.err


def test_step6_prelude_writes_step5d_before_second_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)
    original_touch = design_lifecycle._touch  # pyright: ignore[reportPrivateUsage]
    calls: list[list[str]] = []

    def fake_touch(path: Path) -> None:
        original_touch(path)
        if path == design / ".completed" / "step-5d":
            (design / ".pause-requested").write_text("", encoding="utf-8")

    def fake_pause(argv: list[str]) -> int:
        assert (design / ".completed" / "step-5d").is_file()
        calls.append(argv)
        return 7

    monkeypatch.setattr(design_lifecycle, "_touch", fake_touch)
    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause)
    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 7
    assert len(calls) == 1


def test_step6_cleanup_deletion_path_validates_requires_and_writes_sentinel_before_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design)
    order: list[str] = []

    def fake_validate(candidate: str) -> Path:
        assert candidate == str(design)
        order.append("validate")
        return design

    def fake_require() -> int:
        assert order == ["validate"]
        order.append("require")
        return 0

    def fake_cleanup(argv: list[str]) -> int:
        assert order == ["validate", "require"]
        assert argv == ["--dir", str(design)]
        assert (design / ".completed" / "step-6").is_file()
        order.append("cleanup")
        return 0

    monkeypatch.setattr(design_lifecycle, "_validate_design_tmpdir_arg", fake_validate)
    monkeypatch.setattr(design_lifecycle, "_design_require_plugin_root", fake_require)
    monkeypatch.setattr(session_env, "cleanup_tmpdir_main", fake_cleanup)

    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    assert order == ["validate", "require", "cleanup"]


def test_step6_combined_skips_cleanup_when_prelude_saves_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_DISABLE, "1")

    def fake_prelude(_argv: Sequence[str]) -> int:
        (design / ".pause-save-complete").write_text("", encoding="utf-8")
        return 0

    def fail_cleanup(_argv: Sequence[str]) -> int:
        raise AssertionError("cleanup should not run after pause-save")

    monkeypatch.setattr(design_lifecycle, "step6_prelude_core", fake_prelude)
    monkeypatch.setattr(design_lifecycle, "step6_cleanup_core", fail_cleanup)
    assert design_lifecycle.step6_main(_step6_args(env_path)) == 0


def test_step6_combined_removes_stale_pause_marker_after_rehydrate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = _write_session_env(tmp_path, design, None)
    (design / ".pause-save-complete").write_text("stale\n", encoding="utf-8")
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_DISABLE, "1")
    calls: list[str] = []

    def fake_prelude(_argv: Sequence[str]) -> int:
        calls.append("prelude")
        assert not (design / ".pause-save-complete").exists()
        return 0

    def fake_cleanup(_argv: Sequence[str]) -> int:
        calls.append("cleanup")
        return 0

    monkeypatch.setattr(design_lifecycle, "step6_prelude_core", fake_prelude)
    monkeypatch.setattr(design_lifecycle, "step6_cleanup_core", fake_cleanup)
    assert design_lifecycle.step6_main(_step6_args(env_path)) == 0
    assert calls == ["prelude", "cleanup"]


def test_step6_sidecar_has_authority_over_session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch, PLAN_WRITE_OK="true", CLEANUP_ELIGIBLE="true")
    _write_step5c_status(design, plan_write_ok="false")

    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 0
    assert "plan write did not succeed" in capsys.readouterr().out
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    assert "plan write did not succeed" in capsys.readouterr().out
    assert not (design / ".completed" / "step-5d").exists()
    assert not (design / ".completed" / "step-6").exists()


def test_step6_cleanup_preserves_publish_failure_from_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, publish_ok="false", session_id="run-1")
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    out = capsys.readouterr().out
    assert "publish did not complete" in out
    assert "CLEANUP_STATUS=preserved" in out
    assert not (design / ".completed" / "step-6").exists()


def test_step6_cleanup_preserves_cleanup_ineligible_from_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, cleanup_eligible="false")
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    assert "cleanup not eligible" in capsys.readouterr().out
    assert not (design / ".completed" / "step-6").exists()


def test_step6_cleanup_preserves_standalone_heavy_before_later_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    _write_step5c_status(design, standalone_heavy_failed="true", publish_ok="false", session_id="run-1", cleanup_eligible="false")
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    out = capsys.readouterr().out
    assert "standalone heavy failed" in out
    assert "publish did not complete" not in out
    assert "cleanup not eligible" not in out


def test_step6_empty_design_tmpdir_defers_validation_and_preserves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_path = _step6_env_without_plugin_root(tmp_path, tmp_path, monkeypatch, design_tmpdir="")

    def fail_validate(_candidate: str) -> Path:
        raise AssertionError("empty tmpdir skip/preserve paths must not validate")

    monkeypatch.setattr(design_lifecycle, "_validate_design_tmpdir_arg", fail_validate)
    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 0
    assert "STEP6_PRELUDE_STATUS=skipped" in capsys.readouterr().out
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    assert "CLEANUP_STATUS=preserved" in capsys.readouterr().out


def test_step6_empty_tmpdir_ignores_cwd_bg_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".bg-wait-active").write_text("", encoding="utf-8")
    env_path = _step6_env_without_plugin_root(tmp_path, tmp_path, monkeypatch, design_tmpdir="")

    assert design_lifecycle._step6_in_flight("") is False  # pyright: ignore[reportPrivateUsage]
    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 0
    prelude = capsys.readouterr()
    assert "STEP6_PRELUDE_STATUS=skipped" in prelude.out
    assert "appears still in-flight" not in prelude.err
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 0
    cleanup = capsys.readouterr()
    assert "CLEANUP_STATUS=preserved" in cleanup.out
    assert "appears still in-flight" not in cleanup.err


def test_step6_nonempty_tmpdir_bg_marker_remains_in_flight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design, env_path = _step6_design(tmp_path, monkeypatch)
    (design / ".bg-wait-active").write_text("", encoding="utf-8")
    assert design_lifecycle.step6_prelude_core(_step6_args(env_path)) == 1
    assert "appears still in-flight" in capsys.readouterr().err
    assert design_lifecycle.step6_cleanup_core(_step6_args(env_path)) == 1
    assert "appears still in-flight" in capsys.readouterr().err


def test_step6_main_machine_rows_visible_under_inherited_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _design, env_path = _step6_design(tmp_path, monkeypatch)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
    monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, "999999")
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = design_lifecycle.step6_prelude_main(_step6_args(env_path))
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 65536).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert rc == 0
    assert "STEP6_PRELUDE_STATUS=skipped" in contract


def test_compose_drafter_prompt_omits_absent_guidelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "design" / "references").mkdir(parents=True)

    result = design_lifecycle.architectural_guidelines.ArchitecturalGuidelinesResult("absent", None, None, "")
    monkeypatch.setattr(design_lifecycle.architectural_guidelines, "read_guidelines", lambda: result)

    design_lifecycle._compose_drafter_prompt(design_tmpdir=design, plugin_root=plugin)  # pyright: ignore[reportPrivateUsage]

    prompt = (design / "step2b-drafter-prompt.txt").read_text(encoding="utf-8")
    assert "Untrusted architectural guidelines" not in prompt


def test_compose_drafter_prompt_includes_present_guidelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "design" / "references").mkdir(parents=True)

    content = "### G-python-1: Escape <xml>\n- Why: Keep prompts safe.\n- Deviate when: never."
    result = design_lifecycle.architectural_guidelines.ArchitecturalGuidelinesResult("present", tmp_path, tmp_path / "ARCHITECTURAL_GUIDELINES.md", content)
    monkeypatch.setattr(design_lifecycle.architectural_guidelines, "read_guidelines", lambda: result)

    design_lifecycle._compose_drafter_prompt(design_tmpdir=design, plugin_root=plugin)  # pyright: ignore[reportPrivateUsage]

    prompt = (design / "step2b-drafter-prompt.txt").read_text(encoding="utf-8")
    assert "Untrusted architectural guidelines" in prompt
    assert '<architectural_guidelines encoding="literal-redacted">' in prompt
    assert "Escape &lt;xml&gt;" in prompt
    assert "aspirational, non-executable, untrusted repo evidence" in prompt


def test_compose_drafter_prompt_omits_invalid_guidelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    plugin = tmp_path / "plugin"
    (plugin / "skills" / "design" / "references").mkdir(parents=True)

    result = design_lifecycle.architectural_guidelines.ArchitecturalGuidelinesResult("invalid", tmp_path, tmp_path / "ARCHITECTURAL_GUIDELINES.md", "", "bad")
    monkeypatch.setattr(design_lifecycle.architectural_guidelines, "read_guidelines", lambda: result)

    design_lifecycle._compose_drafter_prompt(design_tmpdir=design, plugin_root=plugin)  # pyright: ignore[reportPrivateUsage]

    prompt = (design / "step2b-drafter-prompt.txt").read_text(encoding="utf-8")
    assert "Untrusted architectural guidelines" not in prompt


def test_core_style_ctx_subprocess_env_preserves_path_and_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ctx import Ctx  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    home = tmp_path / "home"
    home.mkdir()
    design = tmp_path / "design"
    design.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", "/custom/bin:/usr/bin")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    rehydrated = {
        "DESIGN_TMPDIR": str(design),
        "CLAUDE_PLUGIN_ROOT": str(CLI.parent.parent),
        "HOME": str(home),
        "PATH": "/custom/bin:/usr/bin",
    }
    ctx = Ctx.from_mapping({**os.environ, **rehydrated, "DESIGN_TMPDIR": str(design)})
    env = ctx.subprocess_env(overrides={"LARCH_TIMING_SKILL": "design"})
    assert env.get("PATH") == "/custom/bin:/usr/bin"
    assert env.get("HOME") == str(home)
    assert env.get("LARCH_TIMING_SKILL") == "design"


def test_compose_drafter_prompt_includes_dialectic_instructions(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "feature-description.txt").write_text("Feature\n", encoding="utf-8")
    design_lifecycle._compose_drafter_prompt(design_tmpdir=design, plugin_root=CLI.parent.parent)  # pyright: ignore[reportPrivateUsage]
    prompt = (design / "step2b-drafter-prompt.txt").read_text(encoding="utf-8")
    assert "dialectic candidates block" in prompt
    assert "LARCH_DIALECTIC_BEGIN" in prompt
    assert "LARCH_DIALECTIC_END" in prompt
    assert "promoted only after postplan succeeds" in prompt


def _step2b_design_fixture(design: Path) -> None:
    (design / "approach-synthesis.txt").write_text("NO_SKETCHES\n", encoding="utf-8")
    (design / "contested-decisions.md").write_text("NO_CONTESTED_DECISIONS\n", encoding="utf-8")
    (design / "dialectic-resolutions.md").write_text("", encoding="utf-8")
    (design / "feature-description.txt").write_text("feature\n", encoding="utf-8")


def _patch_successful_codex_drafter(monkeypatch: pytest.MonkeyPatch, design: Path) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=str(CLI.parent.parent) + "\n", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            (design / "plan.txt").write_text("## Plan\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("PLAN_WRITTEN=true\n", encoding="utf-8")
        if args[2:4] == ["plan-review", "preview"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[2:4] == ["design", "dialectic-promote-candidates"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)


@pytest.mark.parametrize(
    ("postplan_rc", "stdout_lines", "expected_action", "expected_sidecar"),
    [
        (0, "POSTPLAN_RC=0\nPOSTPLAN_STATUS=ok\n", "step3", None),
        (10, "POSTPLAN_RC=10\nPOSTPLAN_STATUS=validate-failed\n", "postplan-rc10", None),
        (12, "POSTPLAN_RC=12\nPOSTPLAN_STATUS=plan-size-trigger\nsplit prompt\n", "postplan-rc12-split", ".drafter-next-action-rc12.txt"),
        (13, "POSTPLAN_RC=13\nPOSTPLAN_STATUS=partition-requested\npartition prompt\n", "postplan-rc13-partition", ".drafter-next-action-rc13.txt"),
    ],
)
def test_step2b_drafter_emits_next_action_for_postplan_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    postplan_rc: int,
    stdout_lines: str,
    expected_action: str,
    expected_sidecar: str | None,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    _patch_successful_codex_drafter(monkeypatch, design)

    def fake_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(postplan_rc, stdout_lines, "ok")

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    out = capsys.readouterr().out
    assert f"DRAFTER_NEXT_ACTION={expected_action}" in out
    assert "DRAFTER_STATUS=" not in out
    if expected_sidecar is not None:
        assert (design / expected_sidecar).read_text(encoding="utf-8") == stdout_lines


def test_step2b_drafter_inline_retry_uses_post_apply_signals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    _patch_successful_codex_drafter(monkeypatch, design)

    def fake_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        (design / ".step2b-postplan-fallback-used").write_text("true\n", encoding="utf-8")
        return design_lifecycle.PostplanResult(
            10,
            "POSTPLAN_RC=10\nPOSTPLAN_STATUS=validate-failed\nSCOUT_STALE_CLEARED=true\n",
            "validate-failed",
            inline_retry_scheduled=True,
        )

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    assert "DRAFTER_NEXT_ACTION=inline-retry" in capsys.readouterr().out
    assert (design / ".step2b-postplan-fallback-used").read_text(encoding="utf-8") == "true\n"


@pytest.mark.parametrize(("pause_stdout", "expected_rc", "expected_action"), [("PAUSE_OK=true\n", 0, True), ("PAUSE_OK=false\n", 1, False)])
def test_step2b_drafter_rc11_pause_save_gates_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pause_stdout: str,
    expected_rc: int,
    expected_action: bool,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    _patch_successful_codex_drafter(monkeypatch, design)

    def fake_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(11, "POSTPLAN_RC=11\nPOSTPLAN_STATUS=pause-save\n", "pause-save")

    def fake_pause(**_kw: object) -> int:
        print(pause_stdout, end="")
        return 0

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)
    assert design_lifecycle.step2b_drafter_main([]) == expected_rc
    out = capsys.readouterr().out
    assert ("DRAFTER_NEXT_ACTION=postplan-rc11-pause" in out) is expected_action
    assert ("STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1" in out) is expected_action


def test_step2b_drafter_postplan_rc11_pause_after_predrafter_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=str(CLI.parent.parent) + "\n", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            (design / "plan.txt").write_text("## Plan\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("PLAN_WRITTEN=true\n", encoding="utf-8")
            (design / ".pause-requested").write_text("", encoding="utf-8")
        if args[2:4] == ["plan-review", "preview"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def fake_pause(**_kw: object) -> int:
        print("PAUSE_OK=true\n", end="")
        return 0

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_call_pause_save", fake_pause)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    out = capsys.readouterr().out
    assert "DRAFTER_NEXT_ACTION=postplan-rc11-pause" in out
    assert "DRAFTER_NEXT_ACTION=pause-terminal" not in out


def test_step2b_drafter_cleans_dialectic_artifacts_at_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    for name in (
        "dialectic-clarifier-candidates.json",
        "dialectic-clarifier-status.json",
        "dialectic-clarifier-digest.md",
        "dialectic-manual-candidates.json",
        "dialectic-manual-request.txt",
        ".dialectic-raw-pending.json",
    ):
        (design / name).write_text("stale\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "invalid vendor")

    def fail_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        raise AssertionError("postplan should not run when drafter skips")

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fail_postplan)
    design_lifecycle.step2b_drafter_main([])
    for name in (
        "dialectic-clarifier-candidates.json",
        "dialectic-clarifier-status.json",
        "dialectic-clarifier-digest.md",
        "dialectic-manual-candidates.json",
        "dialectic-manual-request.txt",
        ".dialectic-raw-pending.json",
    ):
        assert not (design / name).exists()


def test_step2b_drafter_promotes_only_after_postplan_rc_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")
    promote_calls: list[list[str]] = []
    raw_payload = json.dumps(
        {
            "decisions": [
                {
                    "id": "fork",
                    "title": "Fork",
                    "option_a": "Use SQLite",
                    "option_b": "Use JSON files",
                    "tradeoff": "Different failure modes",
                    "drafter_pick": "option_a",
                    "why_this_matters": "Operator should see it",
                }
            ]
        }
    )

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=str(CLI.parent.parent) + "\n", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            (design / "plan.txt").write_text("## Plan\n\nUse SQLite.\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("PLAN_WRITTEN=true\n", encoding="utf-8")
            (design / ".dialectic-raw-pending.json").write_text(raw_payload, encoding="utf-8")
        if args[2:4] == ["design", "dialectic-promote-candidates"]:
            promote_calls.append(args)
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="DIALECTIC_CANDIDATES_WRITTEN=true\n",
                stderr="",
            )
        if args[2:4] == ["plan-review", "preview"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def fake_postplan_success(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(0, "POSTPLAN_RC=0\n", "ok")

    def fake_postplan_failure(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(1, "POSTPLAN_RC=1\n", "failed")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan_failure)
    assert design_lifecycle.step2b_drafter_main([]) == 1
    assert not promote_calls

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan_success)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    assert len(promote_calls) == 1
    assert promote_calls[0][2:4] == ["design", "dialectic-promote-candidates"]


def test_step2b_drafter_warns_when_dialectic_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=str(CLI.parent.parent) + "\n", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            (design / "plan.txt").write_text("## Plan\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("PLAN_WRITTEN=true\n", encoding="utf-8")
            (design / ".dialectic-raw-pending.json").write_text('{"decisions": []}', encoding="utf-8")
        if args[2:4] == ["design", "dialectic-promote-candidates"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="DIALECTIC_CANDIDATES_WRITTEN=false\nDIALECTIC_CANDIDATES_FAIL_REASON=mismatch\n",
                stderr="",
            )
        if args[2:4] == ["plan-review", "preview"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def fake_postplan_ok(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(0, "POSTPLAN_RC=0\n", "ok")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan_ok)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    assert "dialectic candidate promotion failed after postplan" in capsys.readouterr().err


def test_step2b_drafter_promoted_fingerprint_matches_postplan_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")
    postplan_plan: list[str] = []

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[:3] == ["git", "-C", str(Path.cwd())] and args[3:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=str(CLI.parent.parent) + "\n", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            (design / "plan.txt").write_text("## Draft\n\nUse SQLite.\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("PLAN_WRITTEN=true\n", encoding="utf-8")
            (design / ".dialectic-raw-pending.json").write_text(
                json.dumps(
                    {
                        "decisions": [
                            {
                                "id": "fork",
                                "title": "Fork",
                                "option_a": "Use SQLite",
                                "option_b": "Use JSON files",
                                "tradeoff": "Different failure modes",
                                "drafter_pick": "option_a",
                                "why_this_matters": "Operator should see it",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
        if args[2:4] == ["design", "dialectic-promote-candidates"]:
            buf = StringIO()
            with redirect_stdout(buf):
                design_dialectic.promote_candidates(design)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=buf.getvalue(), stderr="")
        if args[2:4] == ["plan-review", "preview"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def fake_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        (design / "plan.txt").write_text("## Final\n\nUse SQLite for storage.\n\ndiff_lines: 2\n", encoding="utf-8")
        postplan_plan.append(design_dialectic.plan_fingerprint(design))
        design_dialectic.clear_stale(design, reason="plan-rewrite")
        return design_lifecycle.PostplanResult(0, "POSTPLAN_RC=0\n", "ok")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    promoted = json.loads((design / design_dialectic.AUTO_CANDIDATES).read_text(encoding="utf-8"))
    assert postplan_plan
    assert promoted["plan_fingerprint"] == postplan_plan[0]
    assert promoted["plan_fingerprint"] == design_dialectic.plan_fingerprint(design)


def test_step2b_drafter_emits_failsafe_missing_rows_for_unmapped_postplan_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    _patch_successful_codex_drafter(monkeypatch, design)

    def fake_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(3, "POSTPLAN_RC=3\nPOSTPLAN_STATUS=unknown\n", "unknown")

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    out = capsys.readouterr().out
    assert "DRAFTER_NEXT_ACTION=failsafe-missing-rows" in out
    assert "DRAFTER_STATUS=" not in out


def test_step2b_drafter_refuses_conflicting_sentinels_without_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "approach-synthesis.txt").write_text("real sketch\n", encoding="utf-8")
    (design / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    assert design_lifecycle.step2b_drafter_main([]) == 1
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "DRAFTER_NEXT_ACTION=" not in combined
    assert "STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1" not in combined


def test_step2b_drafter_emits_inline_fallback_on_drafter_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    out = capsys.readouterr().out
    assert "DRAFTER_NEXT_ACTION=inline-fallback" in out
    assert "DRAFTER_STATUS=" not in out


def test_step2b_drafter_emits_dirty_tree_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "codex")

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
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        if args[2:4] == ["agent", "launch-codex-drafter"]:
            (design / "plan.txt").write_text("## Plan\n\ndiff_lines: 1\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt").write_text("PLAN_WRITTEN=true\n", encoding="utf-8")
            (design / "step2b-drafter-status.txt.dirty-tree").write_text("STATUS=dirty\nMODE=baseline-delta\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(design_lifecycle.subprocess, "run", fake_run)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    out = capsys.readouterr().out
    assert "DRAFTER_NEXT_ACTION=dirty-tree-recovery" in out
    assert (design / "dirty-tree-detected.env").is_file()


def test_step2b_drafter_clears_stale_inline_retry_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    (design / ".step2b-postplan-inline-retry-pending").write_text("", encoding="utf-8")
    _patch_successful_codex_drafter(monkeypatch, design)

    def fake_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        return design_lifecycle.PostplanResult(
            10,
            "POSTPLAN_RC=10\nPOSTPLAN_STATUS=validate-failed\n",
            "validate-failed",
            inline_retry_scheduled=False,
        )

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fake_postplan)
    assert design_lifecycle.step2b_drafter_main([]) == 0
    out = capsys.readouterr().out
    assert "DRAFTER_NEXT_ACTION=postplan-rc10" in out
    assert "DRAFTER_NEXT_ACTION=inline-retry" not in out
    assert not (design / ".step2b-postplan-inline-retry-pending").exists()


def test_step2b_drafter_cleans_rc12_rc13_sidecars_at_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _step2b_design_fixture(design)
    (design / ".drafter-next-action-rc12.txt").write_text("stale split\n", encoding="utf-8")
    (design / ".drafter-next-action-rc13.txt").write_text("stale partition\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(CLI.parent.parent))
    monkeypatch.setenv("ISSUE_NUMBER", "42")
    monkeypatch.setenv("LARCH_DESIGN_DRAFTER", "invalid vendor")

    def fail_postplan(**_kw: object) -> design_lifecycle.PostplanResult:
        raise AssertionError("postplan should not run when drafter skips")

    monkeypatch.setattr(design_lifecycle, "_shared_step2b_postplan_body", fail_postplan)
    design_lifecycle.step2b_drafter_main([])
    assert not (design / ".drafter-next-action-rc12.txt").exists()
    assert not (design / ".drafter-next-action-rc13.txt").exists()
