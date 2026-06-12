# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
"""Tests for agents.py classification and waterfall."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import agents
import config
from agents import LaunchFailure, TierAttempt

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB_COMMON = REPO_ROOT / "scripts" / "lib-external-launcher-common.sh"


def _bash_classify(*args: str) -> tuple[str, str]:
    script = f'source "{LIB_COMMON}"\nexternal_classify_launch_failure "$@"\n'
    proc = subprocess.run(
        ["bash", "-c", script, "bash", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    cls = ""
    reason = ""
    for line in proc.stdout.splitlines():
        if line.startswith("LAUNCHER_FAILURE_CLASS="):
            cls = line.split("=", 1)[1]
        if line.startswith("LAUNCHER_FAILURE_REASON="):
            reason = line.split("=", 1)[1]
    return cls, reason


def test_parse_launcher_exit_text() -> None:
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=1\n") == 1
    assert agents.parse_launcher_exit_text("noise\nLAUNCHER_EXIT=2\n") == 2
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=bad\n") == 0
    assert agents.parse_launcher_exit_text("") == 0


def test_read_launcher_exit_missing_file_defaults_zero(tmp_path: Path) -> None:
    assert agents.read_launcher_exit(tmp_path / "missing.out") == 0


def test_read_launcher_exit_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "capture.out"
    _ = path.write_text("LAUNCHER_EXIT=3\n", encoding="utf-8")
    assert agents.read_launcher_exit(path) == 3


def test_classify_success() -> None:
    failure = agents.classify_launch_failure(0)
    assert failure == LaunchFailure("none", "")


def test_parse_launcher_failure_class_missing_kv_defaults_health(
    tmp_path: Path,
) -> None:
    log_file = tmp_path / "capture.log"
    _ = log_file.write_text("ordinary launcher output\n", encoding="utf-8")
    assert agents.parse_launcher_failure_class(log_file) == "health"
    assert agents.parse_launcher_failure_class(tmp_path / "missing.log") == "health"
    assert agents.parse_launcher_failure_class(None) == "health"


def test_parse_launcher_failure_class_reads_last_kv(tmp_path: Path) -> None:
    log_file = tmp_path / "capture.log"
    _ = log_file.write_text(
        "LAUNCHER_FAILURE_CLASS=health\nLAUNCHER_FAILURE_CLASS=other\n",
        encoding="utf-8",
    )
    assert agents.parse_launcher_failure_class(log_file) == "other"


def test_classify_timeout() -> None:
    failure = agents.classify_launch_failure(config.EXIT_TIMEOUT)
    assert failure.failure_class == "other"
    assert failure.reason == "timeout"


def test_is_quota_failure(tmp_path: Path) -> None:
    sidecar = tmp_path / "sidecar.log"
    _ = sidecar.write_text("You've hit your usage limit. Try again at 3pm.\n", encoding="utf-8")
    assert agents.is_quota_failure("codex", sidecar) is True
    assert agents.is_quota_failure("cursor", sidecar) is True
    # Unsupported tool and unrelated text do not classify as quota.
    assert agents.is_quota_failure("claude", sidecar) is False
    other = tmp_path / "other.log"
    _ = other.write_text("ordinary failure\n", encoding="utf-8")
    assert agents.is_quota_failure("codex", other) is False
    assert agents.is_quota_failure("codex", tmp_path / "missing.log") is False


def test_classify_quota_is_health(tmp_path: Path) -> None:
    sidecar = tmp_path / "sidecar.log"
    _ = sidecar.write_text("Error: 429 Too Many Requests\n", encoding="utf-8")
    failure = agents.classify_launch_failure(
        1, sidecar, auth_verdict="non-auth", tool="codex",
    )
    # quota is a health-class condition so the waterfall escalates rather than
    # bailing first-fixer-non-health (#3378).
    assert failure == LaunchFailure("health", "quota")


@pytest.mark.skipif(
    not LIB_COMMON.is_file() or shutil.which("bash") is None,
    reason="bash or lib-external-launcher-common.sh unavailable",
)
def test_parity_classify_timeout() -> None:
    py = agents.classify_launch_failure(124)
    bash_cls, bash_reason = _bash_classify("124", "/dev/null", "non-auth", "1", "cursor", "")
    assert py.failure_class == bash_cls
    assert py.reason == bash_reason


@pytest.mark.skipif(
    not LIB_COMMON.is_file() or shutil.which("bash") is None,
    reason="bash or lib-external-launcher-common.sh unavailable",
)
@pytest.mark.parametrize(
    ("launcher_exit", "sidecar_text", "output_text", "auth_verdict", "binary_present", "tool"),
    [
        (127, "", "", "unclassified", "0", "cursor"),
        (1, "", "", "auth", "1", "cursor"),
        (8, "", "", "non-auth", "1", "cursor"),
        (1, "invalid json", "", "non-auth", "1", "cursor"),
        (1, "refused to continue", "", "non-auth", "1", "cursor"),
        (1, "", "parse error", "non-auth", "1", "cursor"),
        (1, "", "refused to continue", "non-auth", "1", "cursor"),
        (99, "", "ordinary failure", "non-auth", "1", "cursor"),
        (1, "You've hit your usage limit. Try again at 3pm.", "", "non-auth", "1", "codex"),
        (1, "", "rate limit exceeded", "non-auth", "1", "cursor"),
    ],
)
def test_parity_classify_launch_failures(
    tmp_path: Path,
    launcher_exit: int,
    sidecar_text: str,
    output_text: str,
    auth_verdict: str,
    binary_present: str,
    tool: str,
) -> None:
    sidecar = tmp_path / "sidecar.log"
    output = tmp_path / "output.txt"
    _ = sidecar.write_text(sidecar_text, encoding="utf-8")
    _ = output.write_text(output_text, encoding="utf-8")
    py = agents.classify_launch_failure(
        launcher_exit,
        sidecar,
        auth_verdict=auth_verdict,
        binary_present=binary_present == "1",
        tool=tool,
        output_file=output,
    )
    bash_cls, bash_reason = _bash_classify(
        str(launcher_exit),
        str(sidecar),
        auth_verdict,
        binary_present,
        tool,
        str(output),
    )
    assert py.failure_class == bash_cls
    assert py.reason == bash_reason


def test_build_launch_argv_conflict_files() -> None:
    argv = agents.build_launch_argv(
        "cursor",
        role=config.FIXER_ROLE,
        output="/tmp/out",
        run_id="run",
        repo="o/r",
        conflict_files="a,b",
    )
    idx = argv.index("--conflict-files")
    assert argv[idx + 1] == "a,b"


@pytest.mark.parametrize("tier", list(config.FIXER_TIER_ORDER))
def test_build_launch_argv_per_tier(tier: str) -> None:
    argv = agents.build_launch_argv(
        tier,
        role="fix",
        output="/tmp/out",
        run_id="run",
        repo="o/r",
    )
    assert argv[:3] == [agents.sys.executable, str(agents._PY_CLI), "agent"]  # pylint: disable=protected-access
    assert argv[3] == f"launch-{tier}-ci"
    assert "--role" in argv


def test_model_args_defaults_and_effort() -> None:
    result = agents.resolve_model_args("codex", with_effort=True)
    assert result.argv[:2] == ("-m", "gpt-5.5")
    assert "-c" in result.argv
    assert 'model_reasoning_effort="high"' in result.argv


def test_model_args_env_rejects_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_MODEL", "   ")
    with pytest.raises(ValueError, match="blank"):
        agents.resolve_model_args("codex")


def test_cursor_model_args_uses_plugin_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LARCH_CURSOR_MODEL", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_CURSOR_MODEL", "cursor-test-model")
    assert agents.resolve_model_args("cursor", with_effort=True).argv == ("--model", "cursor-test-model")


def test_parse_codex_usage_nested_usage(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text(
        '{"msg":{"usage":{"input_tokens":12,"input_tokens_details":{"cached_tokens":5},"output_tokens":7}}}\n',
        encoding="utf-8",
    )
    totals = agents.parse_codex_usage_file(events)
    assert totals.uncached_input_tokens == 7
    assert totals.cached_input_tokens == 5
    assert totals.output_tokens == 7
    assert totals.total_tokens == 19


def test_parse_codex_usage_fails_when_cached_exceeds_input(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text(
        '{"type":"token_usage","input_tokens":3,"cached_input_tokens":4,"output_tokens":1}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cached_tokens exceeds input_tokens"):
        agents.parse_codex_usage_file(events)


def test_cursor_auth_trims_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "  crsr_key  ")
    verdict = agents.cursor_auth_preflight()
    assert verdict.ok is True
    assert verdict.rc == 0
    assert agents.os.environ["CURSOR_API_KEY"] == "crsr_key"


def test_cursor_auth_unsets_blank_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "  \t  ")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Linux")
    verdict = agents.cursor_auth_preflight()
    assert verdict.ok is True
    assert "CURSOR_API_KEY" not in agents.os.environ


def test_validate_conflict_files_rejects_unsafe_paths() -> None:
    assert agents._validate_conflict_files_csv("src/a.py,docs/readme.md") == (True, "")  # pylint: disable=protected-access
    for value in ("../x", "/tmp/x", "src/../x", "src//x", "src/a.py,"):
        ok, _ = agents._validate_conflict_files_csv(value)  # pylint: disable=protected-access
        assert ok is False


def test_ci_failure_log_requires_implement_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "outside.log"
    _ = log.write_text("sk-testsecret0000000000000000\n", encoding="utf-8")
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    ok, _ = agents._validate_failure_log_path(log)  # pylint: disable=protected-access
    assert ok is False
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    ok, _ = agents._validate_failure_log_path(log)  # pylint: disable=protected-access
    assert ok is True
    assert "sk-testsecret" not in agents._read_failure_context(str(log))  # pylint: disable=protected-access


def test_launch_claude_subprocess_uses_stdin_not_prompt_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        "printf '%s\\n' '{\"result\":\"review ok\"}'\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    prompt = tmp_path / "prompt.md"
    secret_prompt = "secret prompt body"
    _ = prompt.write_text(secret_prompt, encoding="utf-8")
    output = tmp_path / "claude.out"
    rc = agents.launch_claude_subprocess_main(
        [
            "--prompt-file",
            str(prompt),
            "--output-file",
            str(output),
            "--timeout",
            "5",
        ],
    )
    assert rc == 0
    meta = output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert secret_prompt not in meta
    assert "CMD_JSON=" in meta
    assert output.read_text(encoding="utf-8") == "review ok"


def test_degraded_tools_empty_presence_is_distinct_bug_signal() -> None:
    result = agents.degraded_tools_result(
        codex_binary_found="true",
        codex_present="",
        cursor_binary_found="true",
        cursor_present="true",
        skill="implement",
    )
    assert result.degraded is True
    assert result.presence_input_empty is True
    assert result.codex_state == "probe-failed"


def test_run_external_agent_writes_meta_done_and_stderr_sink(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    sink = tmp_path / "agent.stderr"
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=5,
        stderr_sink=str(sink),
        cmd=[
            agents.sys.executable,
            "-c",
            "import sys; print('ok'); print('diag', file=sys.stderr)",
        ],
        capture_stdout_only=True,
    )
    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8") == "ok\n"
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "0\n"
    meta = output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert f"STDERR_SINK={sink}" in meta


def test_run_external_agent_missing_child_is_post_validation_failure(tmp_path: Path) -> None:
    output = tmp_path / "missing.out"
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=5,
        cmd=[str(tmp_path / "missing-child")],
    )
    assert result.exit_code == 127
    assert output.with_suffix(output.suffix + ".meta").is_file()
    assert output.with_suffix(output.suffix + ".diag").is_file()
    assert output.with_suffix(output.suffix + ".failure-diag").is_file()
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "127\n"


def test_run_external_agent_args_rejects_timeout_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = agents.run_external_agent_main(
        [
            "--tool",
            "claude",
            "--output",
            str(tmp_path / "out.txt"),
            "--timeout",
            "0",
            "--",
            sys.executable,
            "-c",
            "print('should not run')",
        ],
    )
    assert rc == 1
    assert "--timeout must be a positive integer" in capsys.readouterr().err


def test_health_gate_timeout_resolves_session_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", raising=False)
    session = tmp_path / "session-env.sh"
    _ = session.write_text("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0\n", encoding="utf-8")
    monkeypatch.setenv("SESSION_ENV_PATH", str(session))
    assert agents._health_gate_timeout() is None  # pylint: disable=protected-access
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "5")
    assert agents._health_gate_timeout() == 5  # pylint: disable=protected-access


def test_health_gate_fail_open_on_unparseable_probe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    helper = tmp_path / "scripts" / "check-reviewers.sh"
    helper.parent.mkdir()
    _ = helper.write_text("#!/usr/bin/env bash\nprintf 'unexpected\\n'\n", encoding="utf-8")
    helper.chmod(0o755)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    assert agents._external_health_gate("cursor") == (True, "")  # pylint: disable=protected-access


def test_cursor_auth_prereads_darwin_keychain_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Darwin")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_SECURITY_RC", "0")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "  crsr_from_keychain  ")
    assert agents.cursor_auth_preflight(caller="test").ok is True
    agents.cursor_preread_service_token()
    agents.cursor_auth_export_env()
    assert agents.os.environ["CURSOR_API_KEY"] == "crsr_from_keychain"


def test_auth_retries_acquire_serial_lock_each_attempt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "cursor.out"
    calls: list[str] = []

    def fake_run_external_agent(**kwargs: object) -> agents.RunExternalAgentResult:
        calls.append("run")
        output_arg = kwargs["output"]
        if not isinstance(output_arg, (str, Path)):
            raise TypeError("output must be a path")
        output_path = Path(output_arg)
        _ = output_path.write_text("", encoding="utf-8")
        _ = Path(str(output_path) + ".diag").write_text("authentication failed\n", encoding="utf-8")
        return agents.RunExternalAgentResult(1, output_path)

    def fake_lock(tool: str) -> agents.SerialLockState:
        calls.append(f"lock:{tool}")
        return agents.SerialLockState(None)

    def fake_release(_state: agents.SerialLockState) -> None:
        calls.append("release")

    monkeypatch.setattr(agents, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(agents, "_auth_retry_limit", lambda: 2)
    monkeypatch.setattr(agents, "external_serial_lock_acquire", fake_lock)
    monkeypatch.setattr(agents, "external_serial_lock_release_after", fake_release)
    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="cursor",
        output=output,
        timeout_seconds=5,
        cmd=["cursor"],
    )
    assert result.exit_code == 1
    assert calls == ["lock:cursor", "release", "run", "lock:cursor", "release", "run"]


def test_render_context_files_redacts_and_xml_escapes(tmp_path: Path) -> None:
    ctx = tmp_path / "ctx<&>.txt"
    secret = "sk-" + "A" * 24
    _ = ctx.write_text(f"<tag>{secret}</tag>\n", encoding="utf-8")
    rc, rendered, msg = agents._render_context_files([ctx], [tmp_path])  # pylint: disable=protected-access
    assert (rc, msg) == (0, "")
    assert secret not in rendered
    assert "&lt;tag&gt;" in rendered
    assert 'path="' in rendered
    assert "&lt;" in rendered
    assert "&amp;" in rendered


def test_degraded_tools_gate_flag_precedence_and_both_down(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_PRESENT", "true")
    rc = agents.degraded_tools_gate_main(
        [
            "--codex-binary-found",
            "false",
            "--codex-present",
            "false",
            "--cursor-binary-found",
            "false",
            "--cursor-present",
            "false",
            "--skill",
            "implement",
        ],
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "DEGRADED=true" in out
    assert "BOTH_DOWN=true" in out
    assert "CODEX_STATE=binary-missing" in out


def test_launch_claude_ci_uses_stdin_not_prompt_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    argv_log = tmp_path / "argv.log"
    stdin_log = tmp_path / "stdin.log"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$@\" > \"$CLAUDE_ARGV_LOG\"\n"
        'cat > "$CLAUDE_STDIN_LOG"\n'
        "printf '%s\\n' '{\"result\":\"fixed\"}'\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    monkeypatch.setenv("CLAUDE_ARGV_LOG", str(argv_log))
    monkeypatch.setenv("CLAUDE_STDIN_LOG", str(stdin_log))
    output = tmp_path / "claude-ci.out"
    rc = agents.launch_claude_ci_main(
        [
            "--role",
            "fix",
            "--output",
            str(output),
            "--run-id",
            "run",
            "--repo",
            "o/r",
            "--timeout",
            "5",
        ],
    )
    assert rc == 0
    assert "You are using Claude" not in argv_log.read_text(encoding="utf-8")
    assert "You are using Claude" in stdin_log.read_text(encoding="utf-8")
    assert output.read_text(encoding="utf-8") == "fixed"


def test_launch_claude_subprocess_rejects_prompt_file_outside_safe_roots(tmp_path: Path) -> None:
    prompt = tmp_path / "outside" / "prompt.md"
    prompt.parent.mkdir()
    _ = prompt.write_text("prompt", encoding="utf-8")
    session = tmp_path / "session"
    session.mkdir()
    output = session / "out.txt"
    rc = agents.launch_claude_subprocess_main(
        [
            "--prompt-file",
            str(prompt),
            "--output-file",
            str(output),
            "--timeout",
            "5",
        ],
    )
    assert rc == 2


def test_launch_claude_subprocess_failure_sidecars_and_clean_dirty_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        "printf 'boom\\n' >&2\n"
        "exit 3\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("prompt", encoding="utf-8")
    output = tmp_path / "out.txt"
    rc = agents.launch_claude_subprocess_main(
        [
            "--prompt-file",
            str(prompt),
            "--output-file",
            str(output),
            "--timeout",
            "5",
        ],
    )
    assert rc == 3
    assert "boom" in output.with_suffix(output.suffix + ".stderr-tail").read_text(encoding="utf-8")
    assert output.with_suffix(output.suffix + ".failure-diag").is_file()
    assert "STATUS=clean" in output.with_suffix(output.suffix + ".dirty-tree").read_text(encoding="utf-8")


def test_cursor_ci_stall_monitor_writes_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nsleep 10\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
    monkeypatch.setenv("RUN_EXTERNAL_AGENT_POLL_INTERVAL", "0.05")
    monkeypatch.setenv("LARCH_CURSOR_CI_STALL_THRESHOLD", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "0")
    output = tmp_path / "round-1" / "cursor-ci.out"
    output.parent.mkdir()
    rc = agents.launch_cursor_ci_main(
        [
            "--role",
            "fix",
            "--output",
            str(output),
            "--run-id",
            "run",
            "--repo",
            "o/r",
            "--timeout",
            "5",
        ],
    )
    assert rc == 0
    assert output.with_suffix(output.suffix + ".stall.json").is_file()
    assert any(output.parent.glob("cursor-ci-stall-*.json"))


def test_waterfall_short_circuits_on_first_other(tmp_path: Path) -> None:
    tiers = list(config.FIXER_TIER_ORDER)
    log_file = tmp_path / "capture.log"
    _ = log_file.write_text("LAUNCHER_FAILURE_CLASS=other\n", encoding="utf-8")

    def launch_fn(tier: str) -> TierAttempt:
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "unknown"),
            failure_log=log_file,
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier is None
    assert result.short_circuited is True
    assert len(result.attempts) == 1


def test_waterfall_reverts_paths_between_failed_tiers() -> None:
    tiers = ["cursor", "codex"]
    calls: list[str] = []
    revert_calls: list[tuple[str, ...]] = []
    diff_calls = {"n": 0}

    class RevertRunner:
        def run(
            self,
            argv: list[str],
            *,
            timeout: float | None = None,  # pylint: disable=unused-argument
            cwd: str | None = None,  # pylint: disable=unused-argument
            env: object | None = None,  # pylint: disable=unused-argument
            check: bool = False,  # pylint: disable=unused-argument
        ) -> object:
            _ = timeout, env, check
            key = tuple(argv)
            revert_calls.append(key)
            if key == ("git", "diff", "--name-only", "HEAD"):
                diff_calls["n"] += 1
                stdout = "" if diff_calls["n"] == 1 else "dirty.txt\n"
                return type("R", (), {"stdout": stdout, "returncode": 0})()
            if key == ("git", "ls-files", "--others", "--exclude-standard"):
                return type("R", (), {"stdout": "", "returncode": 0})()
            if key[:3] == ("git", "restore", "--staged"):
                return type("R", (), {"stdout": "", "returncode": 0})()
            if key[:3] == ("git", "checkout", "--"):
                return type("R", (), {"stdout": "", "returncode": 0})()
            return type("R", (), {"stdout": "", "returncode": 0})()

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "auth"),
        )

    result = agents.run_waterfall(
        tiers,
        launch_fn,
        runner=RevertRunner(),  # type: ignore[arg-type]
    )
    assert result.winning_tier is None
    assert calls == ["cursor", "codex"]
    assert ("git", "restore", "--staged", "--", "dirty.txt") in revert_calls


def test_waterfall_falls_through_health() -> None:
    tiers = list(config.FIXER_TIER_ORDER)
    calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        if tier == tiers[-1]:
            return TierAttempt(
                tier=tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            )
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "auth"),
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier == tiers[-1]
    assert len(calls) == len(tiers)


def test_waterfall_rotates_first_tier(tmp_path: Path) -> None:
    tiers = ["cursor", "codex", "claude"]
    calls: list[str] = []
    log_file = tmp_path / "capture.log"
    _ = log_file.write_text("LAUNCHER_FAILURE_CLASS=other\n", encoding="utf-8")

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "unknown"),
            failure_log=log_file,
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier="codex")
    assert calls == ["codex"]
    assert result.short_circuited is True


def test_waterfall_continues_on_wrapper_rc_2() -> None:
    tiers = list(config.FIXER_TIER_ORDER)
    calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        if tier == tiers[0]:
            return TierAttempt(
                tier=tier,
                wrapper_rc=2,
                launcher_exit=0,
                failure=LaunchFailure("other", "validation"),
            )
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=0,
            failure=LaunchFailure("none", ""),
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier == tiers[1]
    assert len(calls) == 2
    assert result.short_circuited is False


def test_waterfall_first_tier_absent_from_tiers_short_circuits(tmp_path: Path) -> None:
    tiers = ["cursor", "codex"]
    log_file = tmp_path / "capture.log"
    _ = log_file.write_text("LAUNCHER_FAILURE_CLASS=other\n", encoding="utf-8")

    def launch_fn(tier: str) -> TierAttempt:
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("health", "unknown"),
            failure_log=log_file,
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier="claude")
    assert result.short_circuited is True
    assert result.attempts[0].tier == "cursor"


def test_waterfall_classify_other_without_kv_short_circuits() -> None:
    tiers = list(config.FIXER_TIER_ORDER)
    calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("other", "unknown"),
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier is None
    assert len(calls) == 1
    assert result.short_circuited is True


def test_waterfall_continues_when_log_missing_failure_class_kv(
    tmp_path: Path,
) -> None:
    tiers = list(config.FIXER_TIER_ORDER)
    calls: list[str] = []
    log_file = tmp_path / "capture.log"
    _ = log_file.write_text("ordinary launcher output\n", encoding="utf-8")

    def launch_fn(tier: str) -> TierAttempt:
        calls.append(tier)
        if tier == tiers[-1]:
            return TierAttempt(
                tier=tier,
                wrapper_rc=0,
                launcher_exit=0,
                failure=LaunchFailure("none", ""),
            )
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=1,
            failure=LaunchFailure("other", "unknown"),
            failure_log=log_file,
        )

    result = agents.run_waterfall(tiers, launch_fn, first_tier=tiers[0])
    assert result.winning_tier == tiers[-1]
    assert len(calls) == len(tiers)
    assert result.short_circuited is False


@pytest.mark.skipif(
    not LIB_COMMON.is_file() or shutil.which("bash") is None,
    reason="bash or lib-external-launcher-common.sh unavailable",
)
def test_parity_classify_success() -> None:
    py = agents.classify_launch_failure(0)
    bash_cls, bash_reason = _bash_classify(
        "0",
        "/dev/null",
        "non-auth",
        "1",
        "cursor",
        "",
    )
    assert py.failure_class == bash_cls
    assert py.reason == bash_reason
