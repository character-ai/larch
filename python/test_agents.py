# pyright: reportPrivateUsage=false, reportUnusedCallResult=false
"""Tests for agents.py classification and waterfall."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import agents
import config
from agents import LaunchFailure, TierAttempt
from proc import CommandResult

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


def test_parse_token_record_text() -> None:
    assert agents.parse_token_record_text("noise\nTOKEN_RECORD=/tmp/custom.token-record\n") == "/tmp/custom.token-record"
    assert agents.parse_token_record_text("TOKEN_RECORD=\n") == ""


class TokenIngestRunner:
    def __init__(self, returncodes: Sequence[int] = (0, 0)) -> None:
        self.returncodes = list(returncodes)
        self.calls: list[tuple[tuple[str, ...], Mapping[str, str] | None]] = []

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
        self.calls.append((tuple(argv), None if env is None else dict(env)))
        rc = self.returncodes.pop(0) if self.returncodes else 0
        return CommandResult(tuple(argv), rc, "", "", 0.01)


def test_ingest_launcher_token_sidecar_uses_token_record_and_exports_tmpdir(tmp_path: Path) -> None:
    sidecar = tmp_path / "custom.token-record"
    _ = sidecar.write_text(
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_ci_fix\nMODEL=gpt-test\n",
        encoding="utf-8",
    )
    seen: set[str] = set()
    runner = TokenIngestRunner()
    ok = agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout=f"LAUNCHER_EXIT=0\nTOKEN_RECORD={sidecar}\n",
        output=tmp_path / "ignored.out",
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
        seen=seen,
    )
    assert ok is True
    assert len(runner.calls) == 2
    assert runner.calls[0][0][-4:] == ("--input", str(sidecar), "--tmpdir", str(tmp_path))
    assert runner.calls[1][0][-2:] == ("--input", str(sidecar))
    assert runner.calls[1][1] is not None
    assert runner.calls[1][1]["IMPLEMENT_TMPDIR"] == str(tmp_path)

    duplicate = agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout=f"TOKEN_RECORD={sidecar}\n",
        output=tmp_path / "ignored.out",
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
        seen=seen,
    )
    assert duplicate is False
    assert len(runner.calls) == 2


def test_ingest_launcher_token_sidecar_defaults_to_output_sidecar(tmp_path: Path) -> None:
    output = tmp_path / "cursor.out"
    sidecar = Path(f"{output}.token-record")
    _ = sidecar.write_text("TOOL=cursor\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=cursor_ci_fix\n", encoding="utf-8")
    runner = TokenIngestRunner()
    assert agents.ingest_launcher_token_sidecar(runner, launcher_stdout="", output=output, tmpdir=tmp_path) is True
    assert runner.calls[0][0][-4:] == ("--input", str(sidecar), "--tmpdir", str(tmp_path))


def test_ingest_launcher_token_sidecar_runs_vendor_ingest_after_append_failure(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    _ = Path(f"{output}.token-record").write_text(
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_ci_fix\n",
        encoding="utf-8",
    )
    runner = TokenIngestRunner(returncodes=(2,))
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
    ) is True
    assert len(runner.calls) == 2


def test_ingest_launcher_token_sidecar_retries_append_only_after_vendor_partial_success(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    sidecar = Path(f"{output}.token-record")
    _ = sidecar.write_text(
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_ci_fix\n",
        encoding="utf-8",
    )
    seen: set[str] = set()
    runner = TokenIngestRunner(returncodes=(2, 0, 0))
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
        seen=seen,
    ) is True
    assert f"{sidecar}:append" not in seen
    assert f"{sidecar}:vendor" in seen
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
        seen=seen,
    ) is True
    assert [call[0][3] for call in runner.calls] == [
        "append-record",
        "record-vendor-sidecar",
        "append-record",
    ]
    assert str(sidecar) in seen


def test_ingest_launcher_token_sidecar_returns_false_when_both_ingests_fail(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    _ = Path(f"{output}.token-record").write_text(
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_ci_fix\n",
        encoding="utf-8",
    )
    runner = TokenIngestRunner(returncodes=(2, 3))
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
    ) is False
    assert len(runner.calls) == 2


def test_ingest_launcher_token_sidecar_marks_seen_after_full_success(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    sidecar = Path(f"{output}.token-record")
    seen: set[str] = set()
    runner = TokenIngestRunner()

    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        seen=seen,
    ) is False
    assert str(sidecar) not in seen
    _ = sidecar.write_text(
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_ci_fix\n",
        encoding="utf-8",
    )
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        seen=seen,
    ) is True
    assert str(sidecar) in seen


def test_ingest_launcher_token_sidecar_retries_only_missing_leg_after_partial_failure(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    sidecar = Path(f"{output}.token-record")
    _ = sidecar.write_text(
        "TOOL=codex\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=codex_ci_fix\n",
        encoding="utf-8",
    )
    seen: set[str] = set()
    runner = TokenIngestRunner(returncodes=(0, 3, 0, 0))

    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
        seen=seen,
    ) is True
    assert f"{sidecar}:append" in seen
    assert f"{sidecar}:vendor" not in seen
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout="",
        output=output,
        tmpdir=tmp_path,
        implement_tmpdir=tmp_path,
        seen=seen,
    ) is True
    assert len(runner.calls) == 3
    assert runner.calls[0][0][3] == "append-record"
    assert runner.calls[1][0][3] == "record-vendor-sidecar"
    assert runner.calls[2][0][3] == "record-vendor-sidecar"
    assert str(sidecar) in seen


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
