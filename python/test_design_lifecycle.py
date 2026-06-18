"""Tests for Python /design lifecycle helpers."""
# pyright: reportUnusedCallResult=false

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

import design_lifecycle
import design_pause
import proc as proc_module
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
    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd and "design-stage-terminal-state.sh" in cmd[0]:
            captured.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, "STAGED=true\n", "")
        return real_run(cmd, check=False, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(subprocess, "run", fake_run)

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


def test_step0_session_ignores_degraded_gate_nonzero_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert rc == 0
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
