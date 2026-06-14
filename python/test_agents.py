# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportArgumentType=false
"""Tests for agents.py classification and waterfall."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import agents
import config
from agents import LaunchFailure, TierAttempt
from proc import CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB_COMMON = REPO_ROOT / "scripts" / "lib-external-launcher-common.sh"


@pytest.fixture(autouse=True)
def _clear_run_external_agent_inner_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.delenv("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", raising=False)


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


class IngestRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.envs: list[Mapping[str, str] | None] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        call = tuple(argv)
        self.calls.append(call)
        self.envs.append(env)
        return CommandResult(call, 0, "", "", 0.01)


def test_parse_launcher_exit_text() -> None:
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=1\n") == 1
    assert agents.parse_launcher_exit_text("noise\nLAUNCHER_EXIT=2\n") == 2
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=bad\n") == 0
    assert agents.parse_launcher_exit_text("") == 0


def test_parse_launcher_exit_text_fails_closed_on_wrapper_failure() -> None:
    assert agents.parse_launcher_exit_text("", process_rc=7) == 7
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=bad\n", process_rc=7) == 7
    assert agents.parse_launcher_exit_text("", process_rc=0) == 0
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=bad\n", process_rc=0) == 0
    assert agents.parse_launcher_exit_text("LAUNCHER_EXIT=4\n", process_rc=7) == 4


def test_read_launcher_exit_missing_file_defaults_zero(tmp_path: Path) -> None:
    assert agents.read_launcher_exit(tmp_path / "missing.out") == 0


def test_read_launcher_exit_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "capture.out"
    _ = path.write_text("LAUNCHER_EXIT=3\n", encoding="utf-8")
    assert agents.read_launcher_exit(path) == 3


def test_resolve_launcher_exit_prefers_done_then_captured_then_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capture.out"
    _ = path.write_text("LAUNCHER_EXIT=3\n", encoding="utf-8")
    _ = path.with_suffix(path.suffix + ".done").write_text("5\n", encoding="utf-8")
    assert agents.resolve_launcher_exit("LAUNCHER_EXIT=4\n", path, process_rc=7) == 5

    _ = path.with_suffix(path.suffix + ".done").write_text("bad\n", encoding="utf-8")
    assert agents.resolve_launcher_exit("LAUNCHER_EXIT=4\n", path, process_rc=7) == 4

    assert agents.resolve_launcher_exit("", path, process_rc=7) == 3
    path.unlink()
    assert agents.resolve_launcher_exit("", path, process_rc=7) == 7


def test_ingest_launcher_token_sidecar_uses_stdout_token_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_TOKEN_LEDGER", str(tmp_path / "stale-ledger.jsonl"))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "stale-session")
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path / "design"))
    monkeypatch.setenv("RESEARCH_TMPDIR", str(tmp_path / "research"))
    monkeypatch.setenv("SESSION_ENV_PATH", str(tmp_path / "session.env"))
    runner = IngestRunner()
    seen: set[str] = set()
    token_record = tmp_path / "stdout.token-record"

    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout=f"LAUNCHER_EXIT=0\nTOKEN_RECORD={token_record}\n",
        tmpdir=str(tmp_path),
        implement_tmpdir=str(tmp_path),
        seen=seen,
        cwd=str(tmp_path),
    )

    assert [call[2:4] for call in runner.calls] == [("token", "append-record"), ("token", "record-vendor-sidecar")]
    assert seen == {str(token_record)}
    active_env = runner.envs[-1]
    assert active_env is not None
    assert active_env["IMPLEMENT_TMPDIR"] == str(tmp_path)
    for key in ("LARCH_TOKEN_LEDGER", "LARCH_TOKEN_SESSION_ID", "DESIGN_TMPDIR", "RESEARCH_TMPDIR", "SESSION_ENV_PATH"):
        assert key not in active_env


def test_ingest_launcher_token_sidecar_output_fallback(tmp_path: Path) -> None:
    runner = IngestRunner()
    seen: set[str] = set()
    output = tmp_path / "ci-fix-codex.out"
    fallback = Path(f"{output}.token-record")
    _ = fallback.write_text("TOOL=codex\nTOTAL=1\n", encoding="utf-8")

    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="LAUNCHER_EXIT=0\n",
        output=output,
        tmpdir=str(tmp_path),
        implement_tmpdir=str(tmp_path),
        seen=seen,
        allow_output_fallback=True,
    )

    assert seen == {str(fallback)}
    assert any(call[-1] == str(fallback) for call in runner.calls)


def test_ingest_launcher_token_sidecar_no_output_fallback_when_disabled(tmp_path: Path) -> None:
    runner = IngestRunner()
    output = tmp_path / "ci-fix-claude.out"
    _ = Path(f"{output}.token-record").write_text("TOOL=claude\nTOTAL=1\n", encoding="utf-8")

    assert not agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="LAUNCHER_EXIT=0\n",
        output=output,
        tmpdir=str(tmp_path),
        implement_tmpdir=str(tmp_path),
        seen=set(),
        allow_output_fallback=False,
    )
    assert not runner.calls


def test_ingest_launcher_token_sidecar_missing_returns_false(tmp_path: Path) -> None:
    runner = IngestRunner()
    assert not agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="LAUNCHER_EXIT=0\n",
        output=tmp_path / "missing.out",
        tmpdir=str(tmp_path),
        implement_tmpdir=str(tmp_path),
        seen=set(),
        allow_output_fallback=True,
    )
    assert not runner.calls


def test_ingest_launcher_token_sidecar_dedups_append_but_records_each_time(tmp_path: Path) -> None:
    runner = IngestRunner()
    seen: set[str] = set()
    token_record = tmp_path / "repeat.token-record"
    stdout = f"TOKEN_RECORD={token_record}\n"

    for _ in range(2):
        assert agents.ingest_launcher_token_sidecar(
            runner,
            launcher_stdout=stdout,
            tmpdir=str(tmp_path),
            implement_tmpdir=str(tmp_path),
            seen=seen,
        )

    append_calls = [call for call in runner.calls if call[2:4] == ("token", "append-record")]
    active_calls = [call for call in runner.calls if call[2:4] == ("token", "record-vendor-sidecar")]
    assert len(append_calls) == 1
    assert len(active_calls) == 2


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


def test_cursor_wrap_prompt_exact_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    rc = agents.cursor_wrap_prompt_main(["hello"])
    assert rc == 0
    assert capsys.readouterr().out == " /max-mode on. Prompt: hello"


def test_read_claude_model_main_unknown_fallback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> agents.CommandResult:
        return agents.CommandResult((), 0, "", "", 0.0)

    monkeypatch.setattr(agents.proc, "run", fake_run)
    rc = agents.read_claude_model_main([])
    assert rc == 0
    assert capsys.readouterr().out == "CLAUDE_MODEL=unknown\n"


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


def test_parse_codex_usage_preserves_explicit_zeroes(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text(
        '{"msg":{"usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0},'
        '"input_tokens":99,"cached_input_tokens":88,"output_tokens":77},'
        '"usage":{"input_tokens":10,"cached_input_tokens":2,"output_tokens":3}}\n',
        encoding="utf-8",
    )
    totals = agents.parse_codex_usage_file(events)
    assert totals.input_tokens == 99
    assert totals.cached_input_tokens == 88
    assert totals.output_tokens == 77


def test_parse_codex_usage_zero_msg_usage_keeps_sibling_msg_fields(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text(
        '{"msg":{"usage":{"input_tokens":0,"cached_input_tokens":0,"output_tokens":0},'
        '"input_tokens":42,"cached_input_tokens":4,"output_tokens":6},'
        '"usage":{"input_tokens":10,"cached_input_tokens":2,"output_tokens":3}}\n',
        encoding="utf-8",
    )
    totals = agents.parse_codex_usage_file(events)
    assert totals.input_tokens == 42
    assert totals.cached_input_tokens == 4
    assert totals.output_tokens == 6


def test_parse_codex_usage_fails_closed_on_malformed_jsonl(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text(
        '{"type":"token_usage","input_tokens":10,"cached_input_tokens":1,"output_tokens":2}\n'
        '{"type":"token_usage","input_tokens":1\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformed usage event"):
        agents.parse_codex_usage_file(events)


def test_parse_codex_usage_fails_when_usage_stream_has_no_tokens(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text('{"type":"token_usage"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="no usage events"):
        agents.parse_codex_usage_file(events)


def test_parse_codex_usage_fails_when_cached_exceeds_input(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    _ = events.write_text(
        '{"type":"token_usage","input_tokens":3,"cached_input_tokens":4,"output_tokens":1}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cached_tokens exceeds input_tokens"):
        agents.parse_codex_usage_file(events)


def test_record_cursor_usage_ignores_malformed_fields(tmp_path: Path) -> None:
    output = tmp_path / "cursor.out"
    _ = output.write_text('{"usage":{"inputTokens":"not-a-number","outputTokens":1}}\n', encoding="utf-8")
    agents._record_cursor_usage_from_output(output, "cursor_ci_fix")  # pylint: disable=protected-access
    assert not output.with_suffix(output.suffix + ".token-record").exists()
    assert "usage token value is not numeric" in output.with_suffix(output.suffix + ".sidecar").read_text(encoding="utf-8")


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


def test_ci_prompt_redacts_plan_file_secrets(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    secret = "sk-" + "A" * 24
    _ = plan.write_text(f"Plan secret: {secret}\n", encoding="utf-8")
    parser = agents._ci_parser("test")  # pylint: disable=protected-access
    args = parser.parse_args(
        [
            "--role",
            "fix",
            "--output",
            str(tmp_path / "out.txt"),
            "--run-id",
            "run",
            "--repo",
            "o/r",
            "--plan-file",
            str(plan),
        ]
    )
    prompt = agents._ci_prompt("Claude", args)  # pylint: disable=protected-access
    assert secret not in prompt
    assert "<REDACTED-TOKEN>" in prompt


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
            "30",
        ],
    )
    assert rc == 0
    meta = output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert secret_prompt not in meta
    assert "CMD_JSON=" in meta
    assert output.read_text(encoding="utf-8") == "review ok"
    assert "HARD CONSTRAINTS" in output.with_suffix(output.suffix + ".prompt").read_text(encoding="utf-8")


def test_launch_claude_subprocess_missing_binary_writes_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("prompt", encoding="utf-8")
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
    assert rc == 127
    assert output.with_suffix(output.suffix + ".stderr-tail").is_file()
    assert output.with_suffix(output.suffix + ".failure-diag").is_file()
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "127\n"
    stdout = capsys.readouterr().out
    assert "STATUS=ERROR" in stdout
    assert f"OUTPUT_FILE={output}" in stdout


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


def test_run_external_agent_rejects_unsafe_output_without_sidecars(tmp_path: Path) -> None:
    output = tmp_path / "bad\nout.txt"
    rc = agents.run_external_agent_main(
        [
            "--tool",
            "claude",
            "--output",
            str(output),
            "--timeout",
            "5",
            "--",
            sys.executable,
            "-c",
            "print('should not run')",
        ],
    )
    assert rc == 1
    assert not output.exists()
    assert not output.with_suffix(output.suffix + ".done").exists()
    assert not output.with_suffix(output.suffix + ".meta").exists()


def test_run_external_agent_inner_sentinel_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "agent.out"
    monkeypatch.setenv("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", ".inner.done")
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=5,
        cmd=[sys.executable, "-c", "print('ok')"],
        capture_stdout_only=True,
    )
    assert result.exit_code == 0
    assert output.with_suffix(output.suffix + ".inner.done").read_text(encoding="utf-8") == "0\n"
    assert not output.with_suffix(output.suffix + ".done").exists()


def test_run_external_agent_cleans_stale_sidecars_and_supplied_streams(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    for stale in (
        output,
        output.with_suffix(output.suffix + ".done"),
        output.with_suffix(output.suffix + ".inner.done"),
        output.with_suffix(output.suffix + ".meta"),
        output.with_suffix(output.suffix + ".diag"),
        output.with_suffix(output.suffix + ".stderr-tail"),
        output.with_suffix(output.suffix + ".failure-diag"),
        stdout_path,
        stderr_path,
    ):
        _ = stale.write_text("stale", encoding="utf-8")
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=5,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        cmd=[sys.executable, "-c", "import sys; print('new-out'); print('new-err', file=sys.stderr)"],
    )
    assert result.exit_code == 0
    assert stdout_path.read_text(encoding="utf-8") == "new-out\n"
    assert stderr_path.read_text(encoding="utf-8") == "new-err\n"
    assert not output.with_suffix(output.suffix + ".inner.done").exists()
    assert not output.with_suffix(output.suffix + ".stderr-tail").exists()
    assert not output.with_suffix(output.suffix + ".failure-diag").exists()


def test_run_external_agent_codex_stdin_is_devnull(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "0")
    output = tmp_path / "codex.out"
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=5,
        capture_stdout_only=True,
        cmd=[sys.executable, "-c", "import sys; data=sys.stdin.read(); print('empty' if data == '' else 'nonempty')"],
    )
    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8") == "empty\n"


def test_run_external_agent_timeout_keeps_stderr_in_diag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_EXTERNAL_AGENT_POLL_INTERVAL", "0.05")
    output = tmp_path / "agent.out"
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=1,
        capture_stdout_only=True,
        cmd=[sys.executable, "-c", "import sys, time; print('err-before-timeout', file=sys.stderr, flush=True); time.sleep(5)"],
    )
    assert result.exit_code == config.EXIT_TIMEOUT
    diag = output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")
    assert "err-before-timeout" in diag
    assert "Timed out" in diag


def test_run_external_agent_stderr_tail_prefers_diag_for_capture_stdout_only(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=5,
        capture_stdout_only=True,
        cmd=[sys.executable, "-c", "import sys; print('stdout-noise'); print('diag-choice', file=sys.stderr); raise SystemExit(3)"],
    )
    assert result.exit_code == 3
    tail = output.with_suffix(output.suffix + ".stderr-tail").read_text(encoding="utf-8")
    assert "diag-choice" in tail
    assert "stdout-noise" not in tail


def test_compose_failure_diag_orders_failure_carriers(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    sink = tmp_path / "sink.log"
    _ = sink.write_text("sink body\n", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".sidecar").write_text("sidecar body\n", encoding="utf-8")
    _ = output.with_suffix(output.suffix + ".diag").write_text("diag body\n", encoding="utf-8")
    agents._compose_failure_diag(output, sink=str(sink))  # pylint: disable=protected-access
    carrier = output.with_suffix(output.suffix + ".failure-diag").read_text(encoding="utf-8")
    assert carrier.index("===== sink =====") < carrier.index("===== sidecar =====") < carrier.index("===== diag =====")


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


def test_run_external_agent_args_rejects_bad_stderr_sink_without_sidecars(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    rc = agents.run_external_agent_main(
        [
            "--tool",
            "claude",
            "--output",
            str(output),
            "--timeout",
            "5",
            "--stderr-sink",
            str(tmp_path / "bad\nsink.log"),
            "--",
            sys.executable,
            "-c",
            "print('should not run')",
        ],
    )
    assert rc == 1
    assert not output.with_suffix(output.suffix + ".meta").exists()
    assert not output.with_suffix(output.suffix + ".done").exists()


def test_check_reviewers_kv_order_and_skip_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("codex", "cursor"):
        path = bin_dir / name
        _ = path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    rc = agents.check_reviewers_main(["--skip-codex-probe", "--skip-cursor-probe"])
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == [
        "CODEX_BINARY_FOUND=true",
        "CURSOR_BINARY_FOUND=true",
        "CODEX_PRESENT=false",
        "CURSOR_PRESENT=false",
        "CODEX_AVAILABLE=false",
        "CURSOR_AVAILABLE=false",
        "CODEX_PROBE_TIMED_OUT=false",
        "CURSOR_PROBE_TIMED_OUT=false",
    ]


def test_check_reviewers_binary_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    result = agents.check_reviewers(env={"PATH": str(tmp_path / "empty-bin"), "TMPDIR": str(tmp_path)})
    assert result == agents.CheckReviewersResult(codex_binary_found=False, cursor_binary_found=False, codex_present=False, cursor_present=False)


def test_check_reviewers_positive_and_negative_stamp_rules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    env = {"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "USER": "stamp-user"}
    stamp = tmp_path / "larch-codex-login-present-stamp-user.stamp"
    _ = stamp.write_text("true\n", encoding="utf-8")
    assert agents.check_reviewers(skip_cursor_probe=True, env=env).codex_present is True
    _ = stamp.write_text("false\n", encoding="utf-8")
    monkeypatch.setattr(agents, "_run_one_codex_probe", lambda _timeout: 1)
    assert agents.check_reviewers(skip_cursor_probe=True, env=env).codex_present is False
    assert agents.check_reviewers(skip_cursor_probe=True, env={**env, "LARCH_PROBE_NEGATIVE_TTL_SECONDS": "60"}).codex_present is False


def test_check_reviewers_expired_stamp_misses_and_auth_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    stamp = tmp_path / "larch-codex-login-present-larch.stamp"
    _ = stamp.write_text("true\n", encoding="utf-8")
    old = time.time() - 120
    agents.os.utime(stamp, (old, old))
    calls = 0

    def fake_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 2 if calls == 1 else 0

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_EXTERNAL_AUTH_RETRIES": "2"},
    )
    assert result.codex_present is True
    assert calls == 2


def test_check_reviewers_codex_login_and_env_key_stamps_are_isolated(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    _ = (tmp_path / "larch-codex-login-present-larch.stamp").write_text("true\n", encoding="utf-8")
    _ = (tmp_path / "larch-codex-env-key-present-larch.stamp").write_text("false\n", encoding="utf-8")
    base = {"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_NEGATIVE_TTL_SECONDS": "60"}
    assert agents.check_reviewers(skip_cursor_probe=True, env=base).codex_present is True
    assert agents.check_reviewers(skip_cursor_probe=True, env={**base, "OPENAI_API_KEY": "sk-test"}).codex_present is False


def test_check_reviewers_cursor_preflight_rc2_one_shot_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    calls = 0

    def fake_preflight(**_kwargs: object) -> agents.AuthVerdict:
        return agents.AuthVerdict(ok=False, rc=2, message="missing")

    def fake_cursor_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 2

    monkeypatch.setattr(agents, "cursor_auth_preflight", fake_preflight)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", fake_cursor_probe)
    result = agents.check_reviewers(
        skip_codex_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_EXTERNAL_AUTH_RETRIES": "5"},
    )
    assert result.cursor_present is False
    assert calls == 1


def test_check_reviewers_invalid_env_normalization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    seen_timeouts: list[int] = []

    def fake_probe(timeout: int) -> int:
        seen_timeouts.append(timeout)
        return 0

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_PROBE_TIMEOUT_SECONDS": "bad",
            "LARCH_EXTERNAL_AUTH_RETRIES": "0",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is True
    assert seen_timeouts == [30]


def test_check_reviewers_non_auth_failure_no_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    calls = 0

    def fake_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_EXTERNAL_AUTH_RETRIES": "5",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is False
    assert calls == 1


def test_check_reviewers_codex_auth_setup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    probe_calls = 0
    real_probe = agents._run_one_codex_probe

    def counting_probe(timeout: int) -> int:
        nonlocal probe_calls
        probe_calls += 1
        return real_probe(timeout)

    monkeypatch.setattr(agents, "_prepare_codex_home", lambda _home: (1, "codex auth setup failed"))
    monkeypatch.setattr(agents, "_run_one_codex_probe", counting_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert result.codex_present is False
    assert probe_calls == 1


def test_check_reviewers_cursor_setup_chain_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    probe_calls = 0

    def fake_probe(_timeout: int) -> int:
        nonlocal probe_calls
        probe_calls += 1
        return 0

    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", lambda: None)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", fake_probe)
    result = agents.check_reviewers(
        skip_codex_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert result.cursor_present is False
    assert probe_calls == 0


def test_check_reviewers_cursor_private_config_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    cfg_dir = tmp_path / "larch-cursor-cfg-test"
    cfg_dir.mkdir()
    old_cfg = agents.os.environ.get("CURSOR_CONFIG_DIR")

    def fake_setup() -> agents._CursorProbeSetup:
        agents.os.environ["CURSOR_CONFIG_DIR"] = str(cfg_dir)
        return agents._CursorProbeSetup(cfg_tmp=cfg_dir, old_cfg=old_cfg)  # pylint: disable=protected-access

    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", fake_setup)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", lambda _timeout: 0)
    monkeypatch.setattr(
        agents,
        "cursor_auth_preflight",
        lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""),
    )
    agents.check_reviewers(
        skip_codex_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert not cfg_dir.exists()
    assert agents.os.environ.get("CURSOR_CONFIG_DIR") == old_cfg


def test_cursor_probe_setup_chain_ignores_config_copy_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user_cfg = tmp_path / ".cursor" / "cli-config.json"
    user_cfg.parent.mkdir(parents=True)
    _ = user_cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "_probe_tmpdir", lambda: tmp_path)
    monkeypatch.setattr(agents.Path, "home", lambda: tmp_path)

    def fail_copyfile(_src: Path, _dst: Path) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(agents.shutil, "copyfile", fail_copyfile)
    setup = agents._cursor_probe_setup_chain()  # pylint: disable=protected-access
    assert setup is not None
    try:
        assert setup.cfg_tmp.is_dir()
    finally:
        agents._cursor_probe_cleanup_private_config_dir(setup)  # pylint: disable=protected-access


def test_check_reviewers_probe_temp_home_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    monkeypatch.setattr(agents, "_run_one_codex_probe", lambda _timeout: 0)
    agents.check_reviewers(
        skip_cursor_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert not any(path.name.startswith("larch-codex-probe-home-") for path in tmp_path.iterdir())


def test_check_reviewers_codex_argv_no_secrets_in_cmd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    secret = "sk-" + "A" * 24
    seen_cmds: list[Sequence[str]] = []
    real_run_probe = agents._run_probe_command

    def capture_probe(cmd: Sequence[str], **_kwargs: object) -> int:
        seen_cmds.append(list(cmd))
        return 0

    monkeypatch.setattr(agents, "_run_probe_command", capture_probe)
    agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "OPENAI_API_KEY": secret,
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert seen_cmds
    assert not any(secret in str(arg) for cmd in seen_cmds for arg in cmd)
    _ = real_run_probe  # keep reference for lint


def test_run_negotiation_round_cursor_probe_failure_exit_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(
        agents.subprocess,
        "run",
        lambda *_args, **_kwargs: agents.subprocess.CompletedProcess([], 1),
    )
    assert agents.run_negotiation_round("cursor", prompt, output, tmp_path) == 2
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"


def test_run_negotiation_round_codex_auth_setup_failure_exit_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    monkeypatch.setattr(agents, "_prepare_codex_home", lambda _home: (1, "codex auth setup failed"))
    assert agents.run_negotiation_round("codex", prompt, output, tmp_path) == 2
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"


def test_run_negotiation_round_usage_and_missing_prompt(tmp_path: Path) -> None:
    assert agents.run_negotiation_round_main([]) == 1
    output = tmp_path / "keep.txt"
    _ = output.write_text("keep\n", encoding="utf-8")
    rc = agents.run_negotiation_round("codex", tmp_path / "missing.txt", output, tmp_path)
    assert rc == 1
    assert output.read_text(encoding="utf-8") == "keep\n"


def test_run_negotiation_round_codex_success_paths_and_args(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_run(cmd: object, **kwargs: object) -> agents.subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        seen["stdin"] = kwargs.get("stdin")
        stdout = kwargs["stdout"]
        stdout.write('{"type":"token_usage","input_tokens":2,"cached_input_tokens":1,"output_tokens":3}\n')
        Path(output).write_text("ok\n", encoding="utf-8")
        return agents.subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    monkeypatch.setattr(agents.proc, "run", lambda *_args, **_kwargs: agents.CommandResult((), 0, "", "", 0.0))
    rc = agents.run_negotiation_round("codex", prompt, output, tmp_path)
    assert rc == 0
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"
    cmd = seen["cmd"]
    assert isinstance(cmd, list)
    assert cmd[:3] == ["codex", "exec", "--full-auto"]
    assert str(tmp_path) in cmd
    assert "--json" in cmd
    assert str(output) in cmd
    assert 'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"' in cmd
    assert not any("sk-test" in str(arg) for arg in cmd)
    assert (tmp_path / "reply.events.jsonl").is_file()
    assert (tmp_path / "reply.sidecar").is_file()
    assert not any(path.name.startswith("larch-codex-negotiation-home-") for path in tmp_path.iterdir())


def test_run_negotiation_round_codex_failure_and_model_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")

    def fake_run(cmd: object, **kwargs: object) -> agents.subprocess.CompletedProcess[str]:
        kwargs["stderr"].write("auth error\n")
        return agents.subprocess.CompletedProcess(cmd, 7)

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    rc = agents.run_negotiation_round("codex", prompt, output, tmp_path)
    assert rc == 2
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"

    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad model")))
    assert agents.run_negotiation_round("codex", prompt, output, tmp_path) == 1


def test_run_negotiation_round_cursor_preflight_failure_and_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=False, rc=2, message="no auth"))
    assert agents.run_negotiation_round("cursor", prompt, output, tmp_path) == 3
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"

    seen: dict[str, object] = {}

    def fake_run(cmd: object, **kwargs: object) -> agents.subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        kwargs["stdout"].write("cursor ok\n")
        return agents.subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setenv("CURSOR_API_KEY", "crsr-secret")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    assert agents.run_negotiation_round("cursor", prompt, output, tmp_path) == 0
    cmd = seen["cmd"]
    assert isinstance(cmd, list)
    assert cmd[:4] == ["cursor", "agent", "-p", "--force"]
    assert "--workspace" in cmd
    assert not any("crsr-secret" in str(arg) for arg in cmd)
    assert output.read_text(encoding="utf-8") == "cursor ok\n"


@pytest.mark.parametrize("tool", ["codex", "cursor"])
def test_run_negotiation_round_serial_lock_before_spawn(
    tool: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    monkeypatch.setenv("LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME", "Darwin")
    calls: list[str] = []

    def fake_lock(lock_tool: str) -> agents.SerialLockState:
        calls.append(f"lock:{lock_tool}")
        return agents.SerialLockState(None)

    def fake_release(_state: agents.SerialLockState) -> None:
        calls.append("release")

    def fake_run(cmd: object, **kwargs: object) -> agents.subprocess.CompletedProcess[str]:
        calls.append("spawn")
        if tool == "codex":
            stdout = kwargs.get("stdout")
            if stdout is not None:
                stdout.write('{"type":"token_usage","input_tokens":1,"cached_input_tokens":0,"output_tokens":1}\n')
            Path(output).write_text("ok\n", encoding="utf-8")
        else:
            stdout = kwargs.get("stdout")
            if stdout is not None:
                stdout.write("cursor ok\n")
        return agents.subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(agents, "external_serial_lock_acquire", fake_lock)
    monkeypatch.setattr(agents, "external_serial_lock_release_after", fake_release)
    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    if tool == "codex":
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(agents.proc, "run", lambda *_args, **_kwargs: agents.CommandResult((), 0, "", "", 0.0))
    else:
        monkeypatch.setattr(
            agents,
            "cursor_auth_preflight",
            lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""),
        )
    assert agents.run_negotiation_round(tool, prompt, output, tmp_path) == 0
    assert calls[:3] == [f"lock:{tool}", "release", "spawn"]


def test_health_gate_timeout_resolves_session_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", raising=False)
    session = tmp_path / "session-env.sh"
    _ = session.write_text("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0\n", encoding="utf-8")
    monkeypatch.setenv("SESSION_ENV_PATH", str(session))
    assert agents._health_gate_timeout() is None  # pylint: disable=protected-access
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "5")
    assert agents._health_gate_timeout() == 5  # pylint: disable=protected-access


def test_health_gate_invalid_retry_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "bad")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "bad")
    monkeypatch.setattr(
        agents,
        "check_reviewers",
        lambda **_kwargs: (
            agents.CheckReviewersResult(
                codex_binary_found=False,
                cursor_binary_found=True,
                codex_present=False,
                cursor_present=True,
            )
        ),
    )
    assert agents._external_health_gate("cursor") == (True, "")  # pylint: disable=protected-access


def test_serial_lock_invalid_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME", "Darwin")
    monkeypatch.setenv("USER", "larch-test-invalid-env")
    monkeypatch.setenv("LARCH_EXTERNAL_SERIAL_LOCK_TTL", "bad")
    monkeypatch.setenv("LARCH_EXTERNAL_SERIAL_LOCK_TRIES", "bad")
    monkeypatch.setenv("LARCH_EXTERNAL_SERIAL_LOCK_DELAY", "bad")

    class FakeTimer:
        def __init__(self, delay: float, callback: object) -> None:
            self.delay = delay
            self.callback = callback
            self.daemon = False

        def start(self) -> None:
            assert self.delay == 0.5

    monkeypatch.setattr(agents, "Timer", FakeTimer)
    state = agents.external_serial_lock_acquire("cursor")
    try:
        assert state.lock_path is not None
        agents.external_serial_lock_release_after(state)
    finally:
        if state.lock_path is not None:
            state.lock_path.rmdir()


def test_health_gate_fail_open_on_present_but_unparseable_value(monkeypatch: pytest.MonkeyPatch) -> None:
    # Key IS present but value is not "true"/"false" → fail-open (not retry).
    class FakeResult:
        codex_probe_timed_out = False
        cursor_probe_timed_out = False

        def kv_lines(self) -> tuple[str, ...]:
            return ("CURSOR_PRESENT=garbage",)

    monkeypatch.setattr(agents, "check_reviewers", lambda **_kwargs: FakeResult())
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    assert agents._external_health_gate("cursor") == (True, "")  # pylint: disable=protected-access


def test_health_gate_fail_open_on_missing_presence_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResult:
        codex_probe_timed_out = False
        cursor_probe_timed_out = False

        def kv_lines(self) -> tuple[str, ...]:
            return ("unexpected=line",)

    monkeypatch.setattr(agents, "check_reviewers", lambda **_kwargs: FakeResult())
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    assert agents._external_health_gate("cursor") == (True, "")  # pylint: disable=protected-access


def test_health_gate_retry_recovers_with_ttl_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []

    def fake_check_reviewers(**kwargs: object) -> agents.CheckReviewersResult:
        env = dict(kwargs.get("env") or {})  # type: ignore[arg-type]
        calls.append(env)
        present = len(calls) > 1
        return agents.CheckReviewersResult(
            codex_binary_found=True,
            cursor_binary_found=False,
            codex_present=present,
            cursor_present=False,
        )

    monkeypatch.setattr(agents, "check_reviewers", fake_check_reviewers)
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "0")
    assert agents._external_health_gate("codex") == (True, "")  # pylint: disable=protected-access
    assert len(calls) == 2
    assert "LARCH_PROBE_TTL_SECONDS" not in calls[0]
    assert calls[1].get("LARCH_PROBE_TTL_SECONDS") == "0"


def test_health_gate_probe_timeout_fast_fails_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate_attempts = 0

    def fake_check_reviewers(**_kwargs: object) -> agents.CheckReviewersResult:
        nonlocal gate_attempts
        gate_attempts += 1
        return agents.CheckReviewersResult(
            codex_binary_found=True,
            cursor_binary_found=False,
            codex_present=False,
            cursor_present=False,
            codex_probe_timed_out=True,
        )

    monkeypatch.setattr(agents, "check_reviewers", fake_check_reviewers)
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "8")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "0")
    assert agents._external_health_gate("codex") == (False, "health-probe timed out after 1s")  # pylint: disable=protected-access
    assert gate_attempts == 1


def test_health_gate_in_process_path_under_tight_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/false" if name == "codex" else None)
    monkeypatch.setattr(agents, "_run_codex_probes", lambda *_args: (False, True))
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "8")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "0")
    assert agents._external_health_gate("codex") == (False, "health-probe timed out after 1s")  # pylint: disable=protected-access


def test_health_gate_wall_clock_timeout_fast_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def blocking_check_reviewers(**_kwargs: object) -> agents.CheckReviewersResult:
        return agents.CheckReviewersResult(
            codex_binary_found=True,
            cursor_binary_found=False,
            codex_present=False,
            cursor_present=False,
            codex_probe_timed_out=True,
        )

    monkeypatch.setattr(agents, "check_reviewers", blocking_check_reviewers)
    monkeypatch.delenv("SESSION_ENV_PATH", raising=False)
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "8")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "0")
    start = time.time()
    gate_result = agents._external_health_gate("codex")  # pylint: disable=protected-access
    elapsed = time.time() - start
    assert gate_result == (False, "health-probe timed out after 1s")
    assert elapsed < 2.5


@pytest.mark.parametrize(("tool", "expected_rc"), [("codex", 7), ("cursor", 8)])
def test_run_external_agent_health_gate_fast_fails_without_spawn(
    tool: str,
    expected_rc: int,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    marker = tmp_path / "spawned"
    output = tmp_path / f"{tool}.out"
    monkeypatch.setattr(
        agents,
        "check_reviewers",
        lambda **_kwargs: agents.CheckReviewersResult(
            codex_binary_found=tool == "codex",
            cursor_binary_found=tool == "cursor",
            codex_present=False,
            cursor_present=False,
        ),
    )
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "0")
    result = agents.run_external_agent(
        tool=tool,
        output=str(output),
        timeout_seconds=5,
        cmd=[sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('spawned')"],
    )
    assert result.exit_code == expected_rc
    assert not marker.exists()
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == f"{expected_rc}\n"


def test_run_external_agent_health_gate_clears_supplied_sidecars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "codex.out"
    stdout_path = tmp_path / "events.jsonl"
    stderr_path = tmp_path / "sidecar.log"
    _ = stdout_path.write_text("stale usage limit\n", encoding="utf-8")
    _ = stderr_path.write_text("stale auth error\n", encoding="utf-8")
    monkeypatch.setattr(
        agents,
        "check_reviewers",
        lambda **_kwargs: agents.CheckReviewersResult(
            codex_binary_found=True,
            cursor_binary_found=False,
            codex_present=False,
            cursor_present=False,
        ),
    )
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_GATE_SLEEP_SECONDS", "0")
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=5,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        cmd=[sys.executable, "-c", "print('should not run')"],
    )
    assert result.exit_code == 7
    assert not stdout_path.exists()
    assert not stderr_path.exists()


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


def test_launch_codex_exec_promotes_done_and_records_outer_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    home_log = tmp_path / "codex-home.log"
    _ = codex.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "out=''\n"
        "while [ $# -gt 0 ]; do\n"
        '  case "$1" in --output-last-message) out="$2"; shift 2 ;; --) shift; break ;; *) shift ;; esac\n'
        "done\n"
        'printf "%s\\n" "$CODEX_HOME" > "$CODEX_HOME_LOG"\n'
        "printf 'codex final\\n' > \"$out\"\n"
        "printf '%s\\n' '{\"type\":\"token_usage\",\"input_tokens\":10,\"cached_input_tokens\":3,\"output_tokens\":4}'\n",
        encoding="utf-8",
    )
    codex.chmod(0o755)
    workdir = tmp_path / "repo"
    workdir.mkdir()
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("do work", encoding="utf-8")
    output = tmp_path / "codex.out"
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CODEX_HOME_LOG", str(home_log))
    monkeypatch.setenv("LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT", "0")
    rc = agents.launch_codex_exec_main(
        [
            "--output",
            str(output),
            "--timeout",
            "5",
            "--prompt-file",
            str(prompt),
            "--workdir",
            str(workdir),
            "--usage-label",
            "codex_test",
        ],
    )
    assert rc == 0
    assert output.read_text(encoding="utf-8") == "codex final\n"
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "0\n"
    assert not output.with_suffix(output.suffix + ".inner.done").exists()
    assert "OUTER_LAUNCHER=agent launch-codex-exec" in output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert "TOTAL=14" in output.with_suffix(output.suffix + ".token-record").read_text(encoding="utf-8")
    assert "LAUNCHER_EXIT=0" in capsys.readouterr().out
    assert home_log.read_text(encoding="utf-8").strip()


def test_launch_codex_exec_preflight_missing_trusted_instructions_writes_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("do work", encoding="utf-8")
    output = tmp_path / "codex.out"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    rc = agents.launch_codex_exec_main(
        [
            "--output",
            str(output),
            "--timeout",
            "5",
            "--prompt-file",
            str(prompt),
            "--workdir",
            str(workdir),
            "--trusted-instructions-file",
            str(tmp_path / "missing.txt"),
        ],
    )
    assert rc == 0
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "2\n"
    assert "trusted-instructions-file not found" in output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")
    assert "LAUNCHER_FAILURE_CLASS=other" in capsys.readouterr().out


def test_launch_codex_exec_preflight_model_args_writes_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("do work", encoding="utf-8")
    output = tmp_path / "codex.out"
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LARCH_CODEX_MODEL", "   ")
    rc = agents.launch_codex_exec_main(
        [
            "--output",
            str(output),
            "--timeout",
            "5",
            "--prompt-file",
            str(prompt),
            "--workdir",
            str(workdir),
        ],
    )
    assert rc == 0
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "1\n"
    assert "model args failed" in output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")


def test_prepare_codex_home_unreadable_user_config_returns_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    user_codex = home / ".codex"
    user_codex.mkdir(parents=True)
    config_path = user_codex / "config.toml"
    _ = config_path.write_text("keep = true\n", encoding="utf-8")
    config_path.chmod(0o000)
    monkeypatch.setenv("HOME", str(home))
    codex_home = tmp_path / "codex-home"
    rc, msg = agents._prepare_codex_home(codex_home)  # pylint: disable=protected-access
    assert rc == 1
    assert "codex auth setup failed" in msg


def test_prepare_codex_home_merges_trusted_instructions_and_strips_user_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    user_codex = home / ".codex"
    user_codex.mkdir(parents=True)
    _ = (user_codex / "config.toml").write_text(
        "instructions = '''old'''\nmodel_provider = \"openai-larch-env\"\nkeep = true\n",
        encoding="utf-8",
    )
    trusted = tmp_path / "trusted.txt"
    _ = trusted.write_text("trusted body", encoding="utf-8")
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("HOME", str(home))
    rc, msg = agents._prepare_codex_home(codex_home, trusted_instructions_file=str(trusted))  # pylint: disable=protected-access
    assert (rc, msg) == (0, "")
    config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert config_text.startswith("instructions = '''\ntrusted body\n'''")
    assert "old" not in config_text
    assert "openai-larch-env" not in config_text
    assert "keep = true" in config_text


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


def test_ci_prompt_includes_role_specific_recovery_guidance(tmp_path: Path) -> None:
    failure_log = tmp_path / "failure.log"
    _ = failure_log.write_text("pytest failed", encoding="utf-8")
    fix_args = argparse.Namespace(
        role="fix",
        plan_file="",
        failure_log=str(failure_log),
        run_id="run",
        repo="o/r",
        conflict_files="",
    )
    conflict_args = argparse.Namespace(
        role="resolve-conflict",
        plan_file="",
        failure_log="",
        run_id="run",
        repo="o/r",
        conflict_files="a.py",
    )
    assert "Reproduce the failing check locally" in agents._ci_prompt("Codex", fix_args)  # pylint: disable=protected-access
    conflict_prompt = agents._ci_prompt("Codex", conflict_args)  # pylint: disable=protected-access
    assert "stage every resolved file" in conflict_prompt
    assert "git rebase --continue" in conflict_prompt


def test_launch_codex_ci_missing_binary_classifies_health(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty_path = tmp_path / "empty-bin"
    empty_path.mkdir()
    monkeypatch.setenv("PATH", str(empty_path))
    output = tmp_path / "codex-ci.out"
    rc = agents.launch_codex_ci_main(
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
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "127\n"
    stdout = capsys.readouterr().out
    assert "LAUNCHER_FAILURE_CLASS=health" in stdout
    assert "LAUNCHER_FAILURE_REASON=binary-missing" in stdout


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


def test_launch_claude_ci_records_timing_and_token_sidecars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        "printf '%s\\n' '{\"result\":\"fixed\",\"usage\":{\"input_tokens\":10,\"output_tokens\":4,\"cache_read_input_tokens\":2,\"cache_creation_input_tokens\":1}}'\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
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
            "--timing-task-kind",
            "claude-ci-test",
        ],
    )
    assert rc == 0
    token_record = output.with_suffix(output.suffix + ".token-record").read_text(encoding="utf-8")
    assert "TOOL=claude" in token_record
    assert "TOTAL=17" in token_record


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ('{"is_error":true,"result":"backend failed"}', "CLAUDE_CI_ERROR_RESPONSE"),
        ("not-json", "CLAUDE_CI_MALFORMED_JSON"),
        ('{"result":""}', "CLAUDE_CI_EMPTY_RESULT"),
    ],
)
def test_launch_claude_ci_rejects_bad_json_envelopes(
    payload: str,
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        f"printf '%s\\n' {payload!r}\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
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
    assert output.read_text(encoding="utf-8") == f"{expected}\n"
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "1\n"
    assert "LAUNCHER_EXIT=1" in capsys.readouterr().out


def test_launch_cursor_ci_auth_preflight_classifies_as_health_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    monkeypatch.setenv("CURSOR_API_KEY", "")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Darwin")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_SECURITY_RC", "45")
    output = tmp_path / "cursor-ci.out"
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
    stdout = capsys.readouterr().out
    assert "LAUNCHER_FAILURE_CLASS=health" in stdout
    assert "LAUNCHER_FAILURE_REASON=auth" in stdout
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "2\n"


def test_launch_cursor_ci_model_arg_failure_writes_launcher_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    cursor.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    monkeypatch.setenv("CURSOR_API_KEY", "crsr_test")
    monkeypatch.setenv("LARCH_CURSOR_MODEL", " \t ")
    output = tmp_path / "cursor-ci.out"
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
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "1\n"
    diag = output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")
    assert "STATUS=FAILED" in diag
    assert "model args failed" in diag
    assert "LAUNCHER_EXIT=1" in capsys.readouterr().out


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


def test_launch_claude_subprocess_requires_read_tools_add_dir(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("prompt", encoding="utf-8")
    output = tmp_path / "out.txt"
    rc = agents.launch_claude_subprocess_main(
        [
            "--read-tools",
            "--prompt-file",
            str(prompt),
            "--output-file",
            str(output),
            "--timeout",
            "5",
        ],
    )
    assert rc == 2


def test_launch_claude_subprocess_rejects_read_tools_add_dir_outside_session(tmp_path: Path) -> None:
    prompt = tmp_path / "session" / "prompt.md"
    prompt.parent.mkdir()
    _ = prompt.write_text("prompt", encoding="utf-8")
    output = prompt.parent / "out.txt"
    outside = tmp_path / "outside"
    outside.mkdir()
    rc = agents.launch_claude_subprocess_main(
        [
            "--read-tools",
            "--read-tools-add-dir",
            str(outside),
            "--prompt-file",
            str(prompt),
            "--output-file",
            str(output),
            "--timeout",
            "5",
        ],
    )
    assert rc == 2


def test_render_context_files_redacts_secret_shaped_path(tmp_path: Path) -> None:
    secret = "sk-" + "A" * 24
    root = tmp_path / f"context-{secret}"
    root.mkdir()
    ctx = root / "notes.md"
    _ = ctx.write_text("ordinary body\n", encoding="utf-8")
    rc, rendered, msg = agents._render_context_files([ctx], [root])  # pylint: disable=protected-access
    assert rc == 0
    assert msg == ""
    assert secret not in rendered
    assert "&lt;REDACTED-TOKEN&gt;" in rendered


def test_launch_claude_review_forwards_context_files_to_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt = tmp_path / "prompt.md"
    diff = tmp_path / "review.diff"
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.txt"
    scope = tmp_path / "scope.txt"
    for path in (prompt, diff, plan, feature, scope):
        _ = path.write_text(path.name, encoding="utf-8")
    output = tmp_path / "claude-review.out"
    captured: list[str] = []

    def fake_launch(sub_args: list[str]) -> int:
        captured.extend(sub_args)
        _ = output.write_text("ok", encoding="utf-8")
        _ = output.with_suffix(output.suffix + ".done").write_text("0\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(agents, "launch_claude_subprocess_main", fake_launch)
    rc = agents.launch_claude_review_main(
        [
            "--output",
            str(output),
            "--prompt-file",
            str(prompt),
            "--mode",
            "description",
            "--diff-file",
            str(diff),
            "--plan-file",
            str(plan),
            "--feature-file",
            str(feature),
            "--scope-files",
            str(scope),
        ],
    )
    assert rc == 0
    forwarded = [captured[idx + 1] for idx, value in enumerate(captured) if value == "--context-files"]
    assert forwarded == [str(diff), str(plan), str(feature), str(scope)]


def test_launch_claude_review_skips_missing_implicit_context_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt = tmp_path / "prompt.md"
    diff = tmp_path / "review.diff"
    _ = prompt.write_text("prompt", encoding="utf-8")
    _ = diff.write_text("diff", encoding="utf-8")
    output = tmp_path / "claude-review.out"
    captured: list[str] = []

    def fake_launch(sub_args: list[str]) -> int:
        captured.extend(sub_args)
        _ = output.write_text("ok", encoding="utf-8")
        _ = output.with_suffix(output.suffix + ".done").write_text("0\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(agents, "launch_claude_subprocess_main", fake_launch)
    rc = agents.launch_claude_review_main(
        [
            "--output",
            str(output),
            "--prompt-file",
            str(prompt),
            "--diff-file",
            str(diff),
            "--plan-file",
            str(tmp_path / "missing-plan.md"),
            "--feature-file",
            str(tmp_path / "missing-feature.txt"),
        ],
    )
    assert rc == 0
    forwarded = [captured[idx + 1] for idx, value in enumerate(captured) if value == "--context-files"]
    assert forwarded == [str(diff)]


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


@pytest.mark.parametrize("payload", ["not-json", '{"is_error":true,"result":"bad"}', '{"result":""}'])
def test_launch_claude_subprocess_bad_json_envelope_uses_legacy_sentinel(
    payload: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        f"printf '%s\\n' {payload!r}\n",
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
    assert rc == 99
    assert output.read_text(encoding="utf-8") == "CLAUDE_JSON_RESULT_INVALID"
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "99\n"


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
    stall_path = output.with_suffix(output.suffix + ".stall.json")
    assert stall_path.is_file()
    stall = json.loads(stall_path.read_text(encoding="utf-8"))
    assert stall["tool"] == "cursor"
    assert stall["channel"] == "stdout"
    assert stall["capture_phase"] == "pre_sigterm"
    assert isinstance(stall["git_state"], dict)
    assert isinstance(stall["last_transcript_lines"], list)
    assert any(output.parent.glob("cursor-ci-stall-*.json"))


def test_launch_cursor_ci_rejects_invalid_argv_before_spawn(tmp_path: Path) -> None:
    output = tmp_path / "cursor-ci.out"
    rc = agents.launch_cursor_ci_main(
        [
            "--role",
            "bad-role",
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
    assert rc == 2
    assert not output.with_suffix(output.suffix + ".done").exists()


def test_stall_kill_terminates_children_before_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> agents.CommandResult:
        assert argv == ["pgrep", "-P", "100"]
        return agents.CommandResult(tuple(argv), 0, "200\n201\n", "", 0.0)

    def fake_kill(pid: int, sig: int) -> None:
        calls.append((pid, sig))

    monkeypatch.setattr(agents.proc, "run", fake_run)
    monkeypatch.setattr(agents.os, "kill", fake_kill)
    def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(agents.time, "sleep", fake_sleep)
    agents._terminate_child_processes_first(100)  # pylint: disable=protected-access
    assert calls == [(200, 15), (201, 15), (100, 15), (200, 9), (201, 9), (100, 9)]


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
