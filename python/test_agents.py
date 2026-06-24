# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportArgumentType=false
"""Tests for agents.py classification and waterfall."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import agents
import config
import logging_util
from agents import LaunchFailure, TierAttempt
from proc import CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clear_run_external_agent_inner_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.delenv("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", raising=False)


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
    assert agents.parse_launcher_exit_text(text="LAUNCHER_EXIT=1\n") == 1
    assert agents.parse_launcher_exit_text(text="noise\nLAUNCHER_EXIT=2\n") == 2
    assert agents.parse_launcher_exit_text(text="LAUNCHER_EXIT=bad\n") == 0
    assert agents.parse_launcher_exit_text(text="") == 0


def test_parse_launcher_exit_text_fails_closed_on_wrapper_failure() -> None:
    assert agents.parse_launcher_exit_text(text="", process_rc=7) == 7
    assert agents.parse_launcher_exit_text(text="LAUNCHER_EXIT=bad\n", process_rc=7) == 7
    assert agents.parse_launcher_exit_text(text="", process_rc=0) == 0
    assert agents.parse_launcher_exit_text(text="LAUNCHER_EXIT=bad\n", process_rc=0) == 0
    assert agents.parse_launcher_exit_text(text="LAUNCHER_EXIT=4\n", process_rc=7) == 4


def test_read_launcher_exit_missing_file_defaults_zero(tmp_path: Path) -> None:
    assert agents.read_launcher_exit(output_file=tmp_path / "missing.out") == 0


def test_read_launcher_exit_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "capture.out"
    _ = path.write_text("LAUNCHER_EXIT=3\n", encoding="utf-8")
    assert agents.read_launcher_exit(output_file=path) == 3


def test_launcher_paths_maps_stable_sidecars(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    suffix = output.suffix
    # Independent (non-mirrored) pin of the stable sidecar suffix mapping: a
    # data table rather than a hand-built LauncherPaths, so this still catches an
    # accidental change to from_output without duplicating its constructor body
    # (pylint duplicate-code R0801). See issue #5076.
    expected_suffixes = {
        "done": ".done",
        "inner_done": ".inner.done",
        "meta": ".meta",
        "sidecar": ".sidecar",
        "diag": ".diag",
        "events": ".events.jsonl",
        "token_record": ".token-record",
        "failure_diag": ".failure-diag",
        "prompt": ".prompt",
        "stderr_tail": ".stderr-tail",
        "stall_json": ".stall.json",
        "stderr": ".stderr",
        "launch_stderr": ".launch-stderr",
        "launcher_stderr": ".launcher-stderr",
        "sidecar_history": ".sidecar.history",
        "events_history": ".events.history",
    }
    paths = agents.LauncherPaths.from_output(output)
    assert paths.output == output
    for attr, suf in expected_suffixes.items():
        assert getattr(paths, attr) == output.with_suffix(suffix + suf), attr
    # Completeness: every LauncherPaths field must be pinned above (output is
    # checked separately), so a newly added field cannot silently bypass this
    # stability check the way it would when this test mirrored the from_output
    # constructor directly.
    assert {f.name for f in fields(agents.LauncherPaths)} == expected_suffixes.keys() | {"output"}
    assert paths.sentinel_done(".inner.done") == paths.inner_done
    with pytest.raises(FrozenInstanceError):
        paths.done = output  # type: ignore[misc]


def test_failure_diag_helpers_use_launcher_paths(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    paths = agents.LauncherPaths.from_output(output)

    candidates = agents._failure_diagnostic_source_candidates(output)  # pylint: disable=protected-access

    assert paths.failure_diag in candidates
    assert paths.sidecar_history in candidates
    assert paths.sidecar in candidates
    assert paths.diag in candidates
    assert paths.events in candidates
    assert paths.stderr in candidates
    assert paths.launch_stderr in candidates
    assert paths.launcher_stderr in candidates

    for source in (
        paths.sidecar_history,
        paths.events_history,
        paths.sidecar,
        paths.diag,
        paths.events,
        paths.stderr,
        paths.launch_stderr,
        paths.launcher_stderr,
    ):
        _ = source.write_text(f"error from {source.name}\n", encoding="utf-8")

    agents._compose_failure_diag(output)  # pylint: disable=protected-access
    diag = paths.failure_diag.read_text(encoding="utf-8")
    assert "===== sidecar.history =====" in diag
    assert "===== events.history (filtered) =====" in diag
    assert "===== stderr =====" in diag


def test_resolve_launcher_exit_prefers_done_then_captured_then_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capture.out"
    _ = path.write_text("LAUNCHER_EXIT=3\n", encoding="utf-8")
    _ = path.with_suffix(path.suffix + ".done").write_text("5\n", encoding="utf-8")
    assert agents.resolve_launcher_exit(captured_text="LAUNCHER_EXIT=4\n", output_file=path, process_rc=7) == 5

    _ = path.with_suffix(path.suffix + ".done").write_text("bad\n", encoding="utf-8")
    assert agents.resolve_launcher_exit(captured_text="LAUNCHER_EXIT=4\n", output_file=path, process_rc=7) == 4

    assert agents.resolve_launcher_exit(captured_text="", output_file=path, process_rc=7) == 3
    path.unlink()
    assert agents.resolve_launcher_exit(captured_text="", output_file=path, process_rc=7) == 7


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


def test_ingest_launcher_token_sidecar_none_effective_tmpdir_first_call(tmp_path: Path) -> None:
    runner = IngestRunner()
    seen: set[str] = set()
    token_record = tmp_path / "retry.token-record"
    stdout = f"TOKEN_RECORD={token_record}\n"

    # First call: no effective tmpdir (tmpdir and implement_tmpdir both None).
    # append-record must be deferred, and the record must stay OUT of `seen` so
    # a later retry with a real tmpdir can still record it.
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout=stdout,
        tmpdir=None,
        implement_tmpdir=None,
        seen=seen,
    )
    assert [call for call in runner.calls if call[2:4] == ("token", "append-record")] == []
    assert seen == set()

    # Second call: tmpdir now available; append-record must run (not silently missed).
    assert agents.ingest_launcher_token_sidecar(
        runner,
        launcher_stdout=stdout,
        tmpdir=str(tmp_path),
        implement_tmpdir=None,
        seen=seen,
    )

    append_calls = [call for call in runner.calls if call[2:4] == ("token", "append-record")]
    active_calls = [call for call in runner.calls if call[2:4] == ("token", "record-vendor-sidecar")]
    assert len(append_calls) == 1
    assert append_calls[0][-1] == str(token_record)
    assert seen == {str(token_record)}
    assert len(active_calls) == 2


def test_classify_success() -> None:
    failure = agents.classify_launch_failure(launcher_exit=0)
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
    failure = agents.classify_launch_failure(launcher_exit=config.EXIT_TIMEOUT)
    assert failure.failure_class == "other"
    assert failure.reason == "timeout"


def test_is_quota_failure(tmp_path: Path) -> None:
    sidecar = tmp_path / "sidecar.log"
    _ = sidecar.write_text("You've hit your usage limit. Try again at 3pm.\n", encoding="utf-8")
    assert agents.is_quota_failure(tool="codex", sidecar=sidecar) is True
    assert agents.is_quota_failure(tool="cursor", sidecar=sidecar) is True
    # Unsupported tool and unrelated text do not classify as quota.
    assert agents.is_quota_failure(tool="claude", sidecar=sidecar) is True
    other = tmp_path / "other.log"
    _ = other.write_text("ordinary failure\n", encoding="utf-8")
    assert agents.is_quota_failure(tool="codex", sidecar=other) is False
    assert agents.is_quota_failure(tool="codex", sidecar=tmp_path / "missing.log") is False


def test_classify_quota_is_health(tmp_path: Path) -> None:
    sidecar = tmp_path / "sidecar.log"
    _ = sidecar.write_text("Error: 429 Too Many Requests\n", encoding="utf-8")
    failure = agents.classify_launch_failure(
        launcher_exit=1, sidecar=sidecar, auth_verdict="non-auth", tool="codex",
    )
    # quota is a health-class condition so the waterfall escalates rather than
    # bailing first-fixer-non-health (#3378).
    assert failure == LaunchFailure("health", "quota")


def test_classify_timeout_expected_output() -> None:
    py = agents.classify_launch_failure(launcher_exit=124)
    assert py.failure_class == "other"
    assert py.reason == "timeout"


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
def test_classify_launch_failures_expected_output(
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
        launcher_exit=launcher_exit,
        sidecar=sidecar,
        auth_verdict=auth_verdict,
        binary_present=binary_present == "1",
        tool=tool,
        output_file=output,
    )
    assert (py.failure_class, py.reason) in {
        ("health", "binary-missing"),
        ("health", "auth"),
        ("health", "health-probe"),
        ("health", "quota"),
        ("other", "parse"),
        ("other", "refusal"),
        ("other", "unknown"),
    }


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


def test_resolve_model_args_ctx_absent_primary_uses_plugin_fallback() -> None:
    from ctx import Ctx  # noqa: PLC0415

    ctx = Ctx.from_mapping({config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL: "plugin-model"})
    assert agents.resolve_model_args("codex", ctx=ctx).argv == ("-m", "plugin-model")


def test_resolve_model_args_ctx_empty_primary_rejects_blank() -> None:
    from ctx import Ctx  # noqa: PLC0415

    ctx = Ctx.from_mapping({config.ENV_LARCH_CODEX_MODEL: "   "})
    with pytest.raises(ValueError, match="blank"):
        agents.resolve_model_args("codex", ctx=ctx)


def test_resolve_model_args_ctx_primary_wins_over_plugin() -> None:
    from ctx import Ctx  # noqa: PLC0415

    ctx = Ctx.from_mapping(
        {
            config.ENV_LARCH_CODEX_MODEL: "primary-model",
            config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL: "plugin-model",
        }
    )
    assert agents.resolve_model_args("codex", ctx=ctx).argv == ("-m", "primary-model")


def test_run_external_agent_inner_sentinel_suffix_ctx_override(tmp_path: Path) -> None:
    from ctx import Ctx  # noqa: PLC0415

    output = tmp_path / "agent.out"
    ctx = Ctx.from_mapping({config.ENV_RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX: ".ctx.done"})
    result = agents.run_external_agent(
        tool="claude",
        output=str(output),
        timeout_seconds=5,
        cmd=[sys.executable, "-c", "print('ok')"],
        capture_stdout_only=True,
        ctx=ctx,
    )
    assert result.exit_code == 0
    assert output.with_suffix(output.suffix + ".ctx.done").is_file()
    assert not output.with_suffix(output.suffix + ".done").exists()


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
    agents._record_cursor_usage_from_output(output=output, label="cursor_ci_fix")  # pylint: disable=protected-access
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
    prompt = agents._ci_prompt(tool="Claude", args=args)  # pylint: disable=protected-access
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
    paths = agents.LauncherPaths.from_output(output)
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    for stale in (
        paths.output,
        paths.done,
        paths.inner_done,
        paths.meta,
        paths.diag,
        paths.stderr_tail,
        paths.failure_diag,
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
    assert not paths.inner_done.exists()
    assert not paths.stderr_tail.exists()
    assert not paths.failure_diag.exists()


def test_record_timing_wrappers_delegate_to_launch_timing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str, float, Path, int]] = []

    def fake_record(tool: str, task_kind: str, start_s: float, output: Path, exit_code: int) -> None:
        calls.append((tool, task_kind, start_s, output, exit_code))

    monkeypatch.setattr(agents, "_record_launch_timing", fake_record)

    output = tmp_path / "agent.out"
    agents._review_record_timing(vendor="codex", task_kind="codex-review", start_s=12.0, output=output, exit_code=7)  # pylint: disable=protected-access
    agents._record_implement_timing(tool="cursor", task_kind="cursor-implement", start=13.0, output=output, exit_code=8)  # pylint: disable=protected-access

    assert calls == [
        ("codex", "codex-review", 12.0, output, 7),
        ("cursor", "cursor-implement", 13.0, output, 8),
    ]


def test_finalize_launch_runs_only_supplied_hooks_in_order(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    paths = agents.LauncherPaths.from_output(output)
    order: list[str] = []

    def first() -> None:
        order.append("first")

    def promote() -> None:
        order.append("promote")
        agents._promote_inner_done(output)  # pylint: disable=protected-access

    def last() -> None:
        order.append("last")

    _ = paths.inner_done.write_text("0\n", encoding="utf-8")
    agents._finalize_launch(hooks=(first, promote, last))  # pylint: disable=protected-access

    assert order == ["first", "promote", "last"]
    assert paths.done.read_text(encoding="utf-8") == "0\n"
    assert not paths.inner_done.exists()


def test_finalize_launch_does_not_promote_without_hook(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    paths = agents.LauncherPaths.from_output(output)
    _ = paths.inner_done.write_text("0\n", encoding="utf-8")

    agents._finalize_launch(hooks=())  # pylint: disable=protected-access

    assert paths.inner_done.read_text(encoding="utf-8") == "0\n"
    assert not paths.done.exists()


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


def test_run_external_agent_non_executable_binary_returns_126(tmp_path: Path) -> None:
    binary = tmp_path / "codex"
    _ = binary.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    binary.chmod(0o644)
    output = tmp_path / "out.txt"
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=5,
        cmd=[str(binary)],
    )
    assert result.exit_code == 126
    assert "Permission denied" in output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "126\n"


def test_run_external_agent_spawns_despite_unhealthy_probe_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEX_PRESENT", "false")
    monkeypatch.setenv("CURSOR_PRESENT", "false")
    popen_calls: list[list[str]] = []

    class _FakeProc:
        pid = 12345

        def wait(self, timeout: float | None = None) -> int:
            _ = timeout
            return 0

        def poll(self) -> int:
            return 0

    def fake_popen(cmd: list[str], **kwargs: object) -> _FakeProc:
        _ = kwargs
        popen_calls.append(list(cmd))
        return _FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    helper = tmp_path / "helper.sh"
    _ = helper.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    helper.chmod(0o755)
    output = tmp_path / "out.txt"
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=5,
        cmd=[str(helper)],
    )
    assert popen_calls == [[str(helper)]]
    assert result.exit_code == 0


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


def test_check_reviewers_cursor_preflight_rc2_transient_rc1_one_shot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    calls = 0
    cfg_dir = tmp_path / "larch-cursor-cfg-test"

    def fake_preflight(**_kwargs: object) -> agents.AuthVerdict:
        return agents.AuthVerdict(ok=False, rc=2, message="missing")

    def fake_setup() -> agents._CursorProbeSetup:
        cfg_dir.mkdir()
        return agents._CursorProbeSetup(cfg_tmp=cfg_dir, old_cfg=None)  # pylint: disable=protected-access

    def fake_cleanup(setup: agents._CursorProbeSetup | None) -> None:
        if setup is not None:
            shutil.rmtree(setup.cfg_tmp, ignore_errors=True)

    def fake_cursor_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(agents, "cursor_auth_preflight", fake_preflight)
    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", fake_setup)
    monkeypatch.setattr(agents, "_cursor_probe_cleanup_private_config_dir", fake_cleanup)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", fake_cursor_probe)
    result = agents.check_reviewers(
        skip_codex_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_EXTERNAL_AUTH_RETRIES": "5",
            "LARCH_PROBE_RETRIES": "2",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
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
        return 0 if len(seen_timeouts) == 3 else 1

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_PROBE_TIMEOUT_SECONDS": "bad",
            "LARCH_EXTERNAL_AUTH_RETRIES": "0",
            "LARCH_PROBE_RETRIES": "bad",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is True
    assert seen_timeouts == [60, 60, 60]


def test_check_reviewers_transient_failure_retries_until_exhausted(
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
    assert result.codex_probe_timed_out is False
    assert calls == 3


def test_check_reviewers_transient_failure_retries_until_success(
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
        return 0 if calls == 2 else 1

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is True
    assert calls == 2


def test_check_reviewers_transient_failure_zero_budget_one_shot(
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
            "LARCH_PROBE_RETRIES": "0",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is False
    assert calls == 1


def test_check_reviewers_probe_no_retry_rc_one_shot(
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
        return agents._PROBE_NO_RETRY_RC

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert result.codex_present is False
    assert calls == 1


def test_check_reviewers_codex_timeout_one_shot_by_default(
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
        return config.EXIT_TIMEOUT

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert result.codex_present is False
    assert result.codex_probe_timed_out is True
    assert calls == 1


def test_check_reviewers_codex_timeout_retry_can_succeed(
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
        return 0 if calls == 2 else config.EXIT_TIMEOUT

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_PROBE_TIMEOUT_RETRIES": "1",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is True
    assert result.codex_probe_timed_out is False
    assert calls == 2


def test_check_reviewers_cursor_timeout_retry_can_succeed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    cfg_dir = tmp_path / "larch-cursor-cfg-test"
    calls = 0

    def fake_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 0 if calls == 2 else config.EXIT_TIMEOUT

    def fake_setup() -> agents._CursorProbeSetup:
        cfg_dir.mkdir()
        return agents._CursorProbeSetup(cfg_tmp=cfg_dir, old_cfg=None)  # pylint: disable=protected-access

    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", fake_setup)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", fake_probe)
    result = agents.check_reviewers(
        skip_codex_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_PROBE_TIMEOUT_RETRIES": "1",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.cursor_present is True
    assert result.cursor_probe_timed_out is False
    assert calls == 2
    assert not cfg_dir.exists()


def test_check_reviewers_invalid_timeout_retry_env_is_one_shot(
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
        return config.EXIT_TIMEOUT

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_PROBE_TIMEOUT_RETRIES": "bad",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is False
    assert result.codex_probe_timed_out is True
    assert calls == 1


def test_check_reviewers_timeout_budget_is_independent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    rcs = [config.EXIT_TIMEOUT, agents._AUTH_RETRY_RC, config.EXIT_TIMEOUT, 1, 0]

    def fake_probe(_timeout: int) -> int:
        return rcs.pop(0)

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_EXTERNAL_AUTH_RETRIES": "2",
            "LARCH_PROBE_RETRIES": "1",
            "LARCH_PROBE_TIMEOUT_RETRIES": "2",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is True
    assert result.codex_probe_timed_out is False
    assert not rcs


def test_check_reviewers_health_gate_unset_probe_retries_one_shot(
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
            "LARCH_EXTERNAL_AUTH_RETRIES": "1",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is False
    assert calls == 1


def test_check_reviewers_health_gate_explicit_probe_retries_override(
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
            "LARCH_EXTERNAL_AUTH_RETRIES": "1",
            "LARCH_PROBE_RETRIES": "2",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is False
    assert calls == 3


def test_check_reviewers_auth_and_transient_budgets_are_independent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)
    rcs = [1, agents._AUTH_RETRY_RC, 1, 0]

    def fake_probe(_timeout: int) -> int:
        return rcs.pop(0)

    monkeypatch.setattr(agents, "_run_one_codex_probe", fake_probe)
    result = agents.check_reviewers(
        skip_cursor_probe=True,
        env={
            "PATH": str(bin_dir),
            "TMPDIR": str(tmp_path),
            "LARCH_EXTERNAL_AUTH_RETRIES": "2",
            "LARCH_PROBE_RETRIES": "2",
            "LARCH_PROBE_TTL_SECONDS": "0",
        },
    )
    assert result.codex_present is True
    assert not rcs


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


def test_check_reviewers_cursor_transient_retry_until_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    cfg_dir = tmp_path / "larch-cursor-cfg-test"
    calls = 0
    cleanup_calls = 0

    def fake_preflight(**_kwargs: object) -> agents.AuthVerdict:
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def fake_setup() -> agents._CursorProbeSetup:
        cfg_dir.mkdir()
        return agents._CursorProbeSetup(cfg_tmp=cfg_dir, old_cfg=None)  # pylint: disable=protected-access

    def fake_cleanup(setup: agents._CursorProbeSetup | None) -> None:
        nonlocal cleanup_calls
        cleanup_calls += 1
        if setup is not None:
            shutil.rmtree(setup.cfg_tmp, ignore_errors=True)

    def fake_cursor_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 0 if calls == 2 else 1

    monkeypatch.setattr(agents, "cursor_auth_preflight", fake_preflight)
    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", fake_setup)
    monkeypatch.setattr(agents, "_cursor_probe_cleanup_private_config_dir", fake_cleanup)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", fake_cursor_probe)
    result = agents.check_reviewers(
        skip_codex_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert result.cursor_present is True
    assert calls == 2
    assert cleanup_calls == 1
    assert not cfg_dir.exists()


def test_check_reviewers_cursor_transient_retry_until_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)
    cfg_dir = tmp_path / "larch-cursor-cfg-test"
    calls = 0
    cleanup_calls = 0

    def fake_preflight(**_kwargs: object) -> agents.AuthVerdict:
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def fake_setup() -> agents._CursorProbeSetup:
        cfg_dir.mkdir()
        return agents._CursorProbeSetup(cfg_tmp=cfg_dir, old_cfg=None)  # pylint: disable=protected-access

    def fake_cleanup(setup: agents._CursorProbeSetup | None) -> None:
        nonlocal cleanup_calls
        cleanup_calls += 1
        if setup is not None:
            shutil.rmtree(setup.cfg_tmp, ignore_errors=True)

    def fake_cursor_probe(_timeout: int) -> int:
        nonlocal calls
        calls += 1
        return 1

    monkeypatch.setattr(agents, "cursor_auth_preflight", fake_preflight)
    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", fake_setup)
    monkeypatch.setattr(agents, "_cursor_probe_cleanup_private_config_dir", fake_cleanup)
    monkeypatch.setattr(agents, "_run_one_cursor_probe", fake_cursor_probe)
    result = agents.check_reviewers(
        skip_codex_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert result.cursor_present is False
    assert result.cursor_probe_timed_out is False
    assert calls == 3
    assert cleanup_calls == 1
    assert not cfg_dir.exists()


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


def test_check_reviewers_codex_probe_resolves_workdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    codex = bin_dir / "codex"
    _ = codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    codex.chmod(0o755)

    def fake_resolve(_cwd: str) -> str:
        return "/resolved/probe-workdir"

    def fake_prepare(_home: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (0, "")

    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", fake_resolve)
    monkeypatch.setattr(agents, "_prepare_codex_home", fake_prepare)
    seen_cmds: list[Sequence[str]] = []

    def capture_probe(cmd: Sequence[str], **_kwargs: object) -> int:
        seen_cmds.append(list(cmd))
        return 0

    monkeypatch.setattr(agents, "_run_probe_command", capture_probe)
    agents.check_reviewers(
        skip_cursor_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert seen_cmds
    cmd = list(seen_cmds[0])
    assert cmd[cmd.index("-C") + 1] == "/resolved/probe-workdir"
    assert 'projects."/resolved/probe-workdir".trust_level="trusted"' in cmd


def test_check_reviewers_cursor_probe_resolves_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cursor = bin_dir / "cursor"
    _ = cursor.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    cursor.chmod(0o755)

    def fake_resolve(_cwd: str) -> str:
        return "/resolved/probe-workdir"

    def cursor_auth_ok(*, caller: str = "agent check-reviewers") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def cleanup_noop(_setup: object) -> None:
        return None

    def setup_chain_stub() -> object:
        return object()

    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", fake_resolve)
    monkeypatch.setattr(agents, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(agents, "_cursor_probe_setup_chain", setup_chain_stub)
    monkeypatch.setattr(agents, "_cursor_probe_cleanup_private_config_dir", cleanup_noop)
    seen_cmds: list[Sequence[str]] = []

    def capture_probe(cmd: Sequence[str], **_kwargs: object) -> int:
        seen_cmds.append(list(cmd))
        return 0

    monkeypatch.setattr(agents, "_run_probe_command", capture_probe)
    agents.check_reviewers(
        skip_codex_probe=True,
        env={"PATH": str(bin_dir), "TMPDIR": str(tmp_path), "LARCH_PROBE_TTL_SECONDS": "0"},
    )
    assert seen_cmds
    cmd = list(seen_cmds[0])
    assert cmd[cmd.index("--workspace") + 1] == "/resolved/probe-workdir"


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
    assert agents.run_negotiation_round(tool="cursor", prompt_file=prompt, output=output, workspace=tmp_path) == 2
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
    assert agents.run_negotiation_round(tool="codex", prompt_file=prompt, output=output, workspace=tmp_path) == 2
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"


def test_run_negotiation_round_usage_and_missing_prompt(tmp_path: Path) -> None:
    assert agents.run_negotiation_round_main([]) == 1
    output = tmp_path / "keep.txt"
    _ = output.write_text("keep\n", encoding="utf-8")
    rc = agents.run_negotiation_round(tool="codex", prompt_file=tmp_path / "missing.txt", output=output, workspace=tmp_path)
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
    rc = agents.run_negotiation_round(tool="codex", prompt_file=prompt, output=output, workspace=tmp_path)
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
    rc = agents.run_negotiation_round(tool="codex", prompt_file=prompt, output=output, workspace=tmp_path)
    assert rc == 2
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"

    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad model")))
    assert agents.run_negotiation_round(tool="codex", prompt_file=prompt, output=output, workspace=tmp_path) == 1


def test_run_negotiation_round_cursor_preflight_failure_and_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=False, rc=2, message="no auth"))
    assert agents.run_negotiation_round(tool="cursor", prompt_file=prompt, output=output, workspace=tmp_path) == 3
    assert capsys.readouterr().out == f"RESPONSE_FILE={output}\n"

    seen: dict[str, object] = {}

    def fake_run(cmd: object, **kwargs: object) -> agents.subprocess.CompletedProcess[str]:
        seen["cmd"] = cmd
        kwargs["stdout"].write("cursor ok\n")
        return agents.subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setenv("CURSOR_API_KEY", "crsr-secret")
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    assert agents.run_negotiation_round(tool="cursor", prompt_file=prompt, output=output, workspace=tmp_path) == 0
    cmd = seen["cmd"]
    assert isinstance(cmd, list)
    assert cmd[:4] == ["cursor", "agent", "-p", "--force"]
    assert "--workspace" in cmd
    assert not any("crsr-secret" in str(arg) for arg in cmd)
    assert output.read_text(encoding="utf-8") == "cursor ok\n"


@pytest.mark.parametrize("tool", ["codex", "cursor"])
def test_run_negotiation_round_startup_lock_before_spawn(
    tool: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.txt"
    output = tmp_path / "reply.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME", "Darwin")
    calls: list[str] = []

    def fake_lock(tool: str) -> agents.StartupLockState:
        calls.append(f"lock:{tool}")
        return agents.StartupLockState(None)

    def fake_release(**_kwargs: object) -> None:
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

    monkeypatch.setattr(agents, "external_startup_lock_acquire", fake_lock)
    monkeypatch.setattr(agents, "external_startup_lock_release_after", fake_release)
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
    assert agents.run_negotiation_round(tool=tool, prompt_file=prompt, output=output, workspace=tmp_path) == 0
    assert calls[:3] == [f"lock:{tool}", "release", "spawn"]



def test_startup_lock_invalid_env_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME", "Darwin")
    monkeypatch.setenv("USER", "larch-test-invalid-env")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TTL", "bad")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TRIES", "bad")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_DELAY", "bad")

    class FakeTimer:
        def __init__(self, delay: float, callback: object) -> None:
            self.delay = delay
            self.callback = callback
            self.daemon = False

        def start(self) -> None:
            assert self.delay == 0.5

    monkeypatch.setattr(agents, "Timer", FakeTimer)
    state = agents.external_startup_lock_acquire(tool="cursor")
    try:
        assert state.lock_path is not None
        assert state.lock_path == Path("/tmp/larch-external-startup-larch-test-invalid-env.lock")
        agents.external_startup_lock_release_after(state=state)
    finally:
        if state.lock_path is not None:
            state.lock_path.rmdir()






@pytest.mark.parametrize(("first_tool", "second_tool"), [("codex", "cursor"), ("cursor", "codex")])
def test_startup_lock_blocks_cross_tool_acquire(
    first_tool: str,
    second_tool: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = f"larch-test-cross-tool-{tmp_path.name}"
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME", "Darwin")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TTL", "60")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TRIES", "1")
    monkeypatch.setenv("USER", user)
    expected = Path(f"/tmp/larch-external-startup-{user}.lock")

    blocked = agents.StartupLockState(None)
    state = agents.external_startup_lock_acquire(tool=first_tool)
    try:
        assert state.lock_path == expected
        assert expected.is_dir()
        blocked = agents.external_startup_lock_acquire(tool=second_tool)
        assert blocked.lock_path is None
    finally:
        for lock_path in (blocked.lock_path, state.lock_path):
            if lock_path is not None:
                with contextlib.suppress(OSError):
                    lock_path.rmdir()


@pytest.mark.parametrize(("python_tool", "second_tool"), [("codex", "cursor"), ("cursor", "codex")])
def test_startup_lock_blocks_second_python_acquire_on_shared_path(
    python_tool: str,
    second_tool: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user = f"larch-test-cross-lane-{tmp_path.name}"
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME", "Darwin")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TTL", "60")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TRIES", "1")
    monkeypatch.setenv("USER", user)
    expected = Path(f"/tmp/larch-external-startup-{user}.lock")

    blocked = agents.StartupLockState(None)
    state = agents.external_startup_lock_acquire(tool=python_tool)
    try:
        assert state.lock_path == expected
        assert expected.is_dir()
        blocked = agents.external_startup_lock_acquire(tool=second_tool)
        assert blocked.lock_path is None
        assert expected.is_dir()
    finally:
        for lock_path in (blocked.lock_path, state.lock_path):
            if lock_path is not None:
                with contextlib.suppress(OSError):
                    lock_path.rmdir()


@pytest.mark.parametrize("user_value", [None, ""])
def test_startup_lock_user_fallback_matches_bash(
    user_value: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME", "Darwin")
    monkeypatch.setenv("LARCH_EXTERNAL_STARTUP_LOCK_TRIES", "1")
    if user_value is None:
        monkeypatch.delenv("USER", raising=False)
    else:
        monkeypatch.setenv("USER", user_value)
    expected = Path("/tmp/larch-external-startup-larch.lock")
    with contextlib.suppress(OSError):
        expected.rmdir()
    state = agents.external_startup_lock_acquire(tool="cursor")
    try:
        assert state.lock_path == expected
    finally:
        if state.lock_path is not None:
            with contextlib.suppress(OSError):
                state.lock_path.rmdir()


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


def test_cursor_auth_preflight_keychain_uses_startup_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_acquire(tool: str) -> agents.StartupLockState:
        calls.append(("acquire", tool))
        return agents.StartupLockState(None)

    def fake_release(state: agents.StartupLockState, delay: float | None = None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        calls.append(("release", str(delay)))

    monkeypatch.setenv("CURSOR_API_KEY", "")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Darwin")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_SECURITY_RC", "0")
    monkeypatch.setattr(agents, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(agents, "external_startup_lock_release_after", fake_release)
    assert agents.cursor_auth_preflight(caller="test").ok is True
    assert calls == [("acquire", "cursor"), ("release", "0")]


def test_cursor_preread_keychain_uses_startup_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_acquire(tool: str) -> agents.StartupLockState:
        calls.append(("acquire", tool))
        return agents.StartupLockState(None)

    def fake_release(state: agents.StartupLockState, delay: float | None = None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        calls.append(("release", str(delay)))

    monkeypatch.setenv("CURSOR_API_KEY", "")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Darwin")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "crsr_from_keychain")
    monkeypatch.setattr(agents, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(agents, "external_startup_lock_release_after", fake_release)
    agents.cursor_preread_service_token()
    assert agents.os.environ["CURSOR_API_KEY"] == "crsr_from_keychain"
    assert calls == [("acquire", "cursor"), ("release", "0")]


def test_cursor_auth_usable_env_key_skips_keychain_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_acquire(tool: str) -> agents.StartupLockState:
        calls.append(tool)
        return agents.StartupLockState(None)

    monkeypatch.setenv("CURSOR_API_KEY", "  crsr_existing_key  ")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Darwin")
    monkeypatch.setattr(agents, "external_startup_lock_acquire", fake_acquire)
    assert agents.cursor_auth_preflight(caller="test").ok is True
    agents.cursor_preread_service_token()
    assert not calls


def test_cursor_auth_non_darwin_skips_keychain_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_acquire(tool: str) -> agents.StartupLockState:
        calls.append(tool)
        return agents.StartupLockState(None)

    monkeypatch.setenv("CURSOR_API_KEY", "")
    monkeypatch.setenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", "1")
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_UNAME", "Linux")
    monkeypatch.setattr(agents, "external_startup_lock_acquire", fake_acquire)
    assert agents.cursor_auth_preflight(caller="test").ok is True
    agents.cursor_preread_service_token()
    assert not calls


def test_auth_retries_acquire_startup_lock_each_attempt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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

    def fake_lock(tool: str) -> agents.StartupLockState:
        calls.append(f"lock:{tool}")
        return agents.StartupLockState(None)

    def fake_release(**_kwargs: object) -> None:
        calls.append("release")

    monkeypatch.setattr(agents, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(agents, "_auth_retry_limit", lambda: 2)
    monkeypatch.setattr(agents, "external_startup_lock_acquire", fake_lock)
    monkeypatch.setattr(agents, "external_startup_lock_release_after", fake_release)
    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="cursor",
        output=output,
        timeout_seconds=5,
        cmd=["cursor"],
    )
    assert result.exit_code == 1
    assert calls == ["lock:cursor", "release", "run", "lock:cursor", "release", "run"]


def test_unclassified_empty_exit_one(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    calls = {"count": 0}

    def fake_run_external_agent(**kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        output_arg = kwargs["output"]
        if not isinstance(output_arg, (str, Path)):
            raise TypeError("output must be a path")
        output_path = Path(output_arg)
        output_path.write_text("", encoding="utf-8")
        exit_code = 1 if calls["count"] == 1 else 4
        return agents.RunExternalAgentResult(exit_code, output_path)

    monkeypatch.setattr(agents, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(agents, "_auth_retry_limit", lambda: 5)
    monkeypatch.setattr(agents, "external_startup_lock_acquire", lambda tool: agents.StartupLockState(None))  # noqa: ARG005
    monkeypatch.setattr(agents, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005
    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="codex",
        output=output,
        timeout_seconds=5,
        cmd=["codex"],
    )
    assert calls["count"] == 2
    assert result.exit_code == 4


def test_unclassified_empty_exit_one_respects_auth_retry_limit_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "codex.out"
    calls = {"count": 0}

    def fake_run_external_agent(**kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        output_arg = kwargs["output"]
        if not isinstance(output_arg, (str, Path)):
            raise TypeError("output must be a path")
        output_path = Path(output_arg)
        output_path.write_text("", encoding="utf-8")
        return agents.RunExternalAgentResult(1, output_path)

    monkeypatch.setattr(agents, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(agents, "_auth_retry_limit", lambda: 1)
    monkeypatch.setattr(agents, "external_startup_lock_acquire", lambda tool: agents.StartupLockState(None))  # noqa: ARG005
    monkeypatch.setattr(agents, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005
    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="codex",
        output=output,
        timeout_seconds=5,
        cmd=["codex"],
    )
    assert calls["count"] == 2
    assert result.exit_code == 1


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
    monkeypatch.delenv("LARCH_CODEX_FIX_MODEL", raising=False)
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
            "--model-role",
            "fix",
        ],
    )
    assert rc == 0
    assert output.read_text(encoding="utf-8") == "codex final\n"
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "0\n"
    assert not output.with_suffix(output.suffix + ".inner.done").exists()
    meta_text = output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert "OUTER_LAUNCHER=agent launch-codex-exec" in meta_text
    assert "OUTER_LAUNCHER_MODEL_ROLE=fix" in meta_text
    assert "MODEL=gpt-5.4-mini" in output.with_suffix(output.suffix + ".token-record").read_text(encoding="utf-8")
    assert "TOTAL=14" in output.with_suffix(output.suffix + ".token-record").read_text(encoding="utf-8")
    assert "LAUNCHER_EXIT=0" in capsys.readouterr().out
    assert home_log.read_text(encoding="utf-8").strip()


def test_launch_codex_exec_default_workdir_resolves_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_cwd = tmp_path / "raw"
    consumer_repo = tmp_path / "consumer"
    raw_cwd.mkdir()
    consumer_repo.mkdir()
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("do work", encoding="utf-8")
    output = tmp_path / "codex.out"
    captured: dict[str, object] = {}

    def fake_resolve(cwd: str) -> str:
        assert cwd == str(raw_cwd)
        return str(consumer_repo)

    def fake_prepare(_home: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return 0, ""

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        captured.update(kwargs)
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text("done\n", encoding="utf-8")
        _ = output_path.with_suffix(output_path.suffix + ".inner.done").write_text("0\n", encoding="utf-8")
        return agents.RunExternalAgentResult(0, output_path)

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(str(arg) for arg in argv), 0, "", "", 0.0)

    monkeypatch.chdir(raw_cwd)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", fake_resolve)
    monkeypatch.setattr(agents, "_prepare_codex_home", fake_prepare)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)

    rc = agents.launch_codex_exec_main(["--output", str(output), "--timeout", "5", "--prompt-file", str(prompt)])

    assert rc == 0
    cmd = list(captured["cmd"])
    assert captured["cwd"] == str(consumer_repo)
    assert cmd[cmd.index("-C") + 1] == str(consumer_repo)
    assert cmd[cmd.index("--add-dir") + 1] == str(consumer_repo)
    assert agents._trust_config_arg(str(consumer_repo)) in cmd


def test_launch_codex_exec_explicit_workdir_is_not_resolved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_cwd = tmp_path / "raw"
    raw_cwd.mkdir()
    prompt = tmp_path / "prompt.md"
    _ = prompt.write_text("do work", encoding="utf-8")
    output = tmp_path / "codex.out"
    captured: dict[str, object] = {}

    def fail_resolve(_cwd: str) -> str:
        raise AssertionError("explicit --workdir must not be resolved")

    def fake_prepare(_home: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return 0, ""

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        captured.update(kwargs)
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text("done\n", encoding="utf-8")
        _ = output_path.with_suffix(output_path.suffix + ".inner.done").write_text("0\n", encoding="utf-8")
        return agents.RunExternalAgentResult(0, output_path)

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(str(arg) for arg in argv), 0, "", "", 0.0)

    monkeypatch.chdir(raw_cwd)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", fail_resolve)
    monkeypatch.setattr(agents, "_prepare_codex_home", fake_prepare)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)

    rc = agents.launch_codex_exec_main(
        ["--output", str(output), "--timeout", "5", "--prompt-file", str(prompt), "--workdir", str(raw_cwd)]
    )

    assert rc == 0
    cmd = list(captured["cmd"])
    assert captured["cwd"] == str(raw_cwd)
    assert cmd[cmd.index("-C") + 1] == str(raw_cwd)


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


def test_review_failure_source_uses_common_resolver_order(tmp_path: Path) -> None:
    output = tmp_path / "review.txt"
    sink = tmp_path / "sink.log"
    ordered = [
        output.with_suffix(output.suffix + ".failure-diag"),
        tmp_path / "review-retry.txt.failure-diag",
        tmp_path / "review-ns-retry.txt.failure-diag",
        sink,
        output.with_suffix(output.suffix + ".sidecar"),
        output.with_suffix(output.suffix + ".diag"),
    ]
    for path in ordered:
        _ = path.write_text(path.name, encoding="utf-8")
    assert agents._review_failure_source(output, sink=str(sink)) == ordered[0]  # pylint: disable=protected-access
    ordered[0].unlink()
    assert agents._review_failure_source(output, sink=str(sink)) == ordered[1]  # pylint: disable=protected-access
    ordered[1].unlink()
    assert agents._review_failure_source(output, sink=str(sink)) == ordered[2]  # pylint: disable=protected-access
    ordered[2].unlink()
    assert agents._review_failure_source(output, sink=str(sink)) == sink  # pylint: disable=protected-access
    sink.unlink()
    assert agents._review_failure_source(output, sink=str(sink)) == output.with_suffix(output.suffix + ".sidecar")  # pylint: disable=protected-access


def test_review_emit_launcher_result_composes_sink_before_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "review.txt"
    sink = tmp_path / "launcher.log"
    _ = output.with_suffix(output.suffix + ".diag").write_text("STATUS=FAILED\n", encoding="utf-8")
    _ = sink.write_text("authentication failed in sink\n", encoding="utf-8")
    seen: dict[str, Path] = {}

    def fake_classify(
        launcher_exit: int,
        sidecar: Path,
        **_kwargs: object,
    ) -> agents.LaunchFailure:
        _ = launcher_exit
        seen["sidecar"] = sidecar
        return agents.LaunchFailure("health", "auth")

    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify)
    agents._review_emit_launcher_result(output=output, tool="cursor", launcher_exit=2, stderr_sink=str(sink))  # pylint: disable=protected-access
    failure_diag = output.with_suffix(output.suffix + ".failure-diag")
    assert seen["sidecar"] == failure_diag
    assert "authentication failed in sink" in failure_diag.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert "LAUNCHER_FAILURE_CLASS=health" in stdout
    assert "LAUNCHER_FAILURE_REASON=auth" in stdout


def test_review_emit_launcher_result_merges_sink_into_existing_failure_diag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "review.txt"
    sink = tmp_path / "launcher.log"
    failure_diag = output.with_suffix(output.suffix + ".failure-diag")
    _ = output.with_suffix(output.suffix + ".diag").write_text("STATUS=FAILED\n", encoding="utf-8")
    _ = failure_diag.write_text("===== diag =====\nstale generic failure\n", encoding="utf-8")
    _ = sink.write_text("authentication failed in sink\n", encoding="utf-8")
    seen: dict[str, Path] = {}

    def fake_classify(
        launcher_exit: int,
        sidecar: Path,
        **_kwargs: object,
    ) -> agents.LaunchFailure:
        _ = launcher_exit
        seen["sidecar"] = sidecar
        return agents.LaunchFailure("health", "auth")

    monkeypatch.setattr(agents, "classify_launch_failure", fake_classify)
    agents._review_emit_launcher_result(output=output, tool="cursor", launcher_exit=2, stderr_sink=str(sink))  # pylint: disable=protected-access
    assert seen["sidecar"] == failure_diag
    assert "authentication failed in sink" in failure_diag.read_text(encoding="utf-8")
    stdout = capsys.readouterr().out
    assert "LAUNCHER_FAILURE_CLASS=health" in stdout
    assert "LAUNCHER_FAILURE_REASON=auth" in stdout


def test_review_append_launch_failure_merges_sink_into_existing_failure_diag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "codex-review.txt"
    sink = tmp_path / "codex-review.log"
    failure_diag = output.with_suffix(output.suffix + ".failure-diag")
    diag = output.with_suffix(output.suffix + ".diag")
    _ = diag.write_text("generic failure\n", encoding="utf-8")
    _ = failure_diag.write_text("===== diag =====\ngeneric failure\n", encoding="utf-8")
    _ = sink.write_text("launcher stderr detail\n", encoding="utf-8")
    monkeypatch.setattr(agents, "_resolve_execution_issues_log", lambda: None)
    agents._review_append_launch_failure(  # pylint: disable=protected-access
        output=output,
        tool="codex",
        exit_code=1,
        stderr_sink=str(sink),
    )
    assert "launcher stderr detail" in failure_diag.read_text(encoding="utf-8")


def test_review_append_launch_failure_threads_custom_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "codex-review.txt"
    _ = output.with_suffix(output.suffix + ".diag").write_text("boom\n", encoding="utf-8")
    log = tmp_path / "execution-issues.md"
    _ = log.write_text("", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents, "_resolve_execution_issues_log", lambda: log)
    captured: dict[str, str] = {}

    def fake_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        a = [str(x) for x in argv]
        if "append-failure" in a:
            captured["site"] = a[a.index("--site") + 1]
        return CommandResult((), 0, "", "", 0.0)

    monkeypatch.setattr(agents.proc, "run", fake_run)
    agents._review_append_launch_failure(output=output, tool="codex", exit_code=1, site="design Step 3")  # pylint: disable=protected-access
    assert captured["site"] == "design Step 3"
    parts_dir = tmp_path / "vendor-failure-diagnostics.parts"
    combined = "".join(p.read_text(encoding="utf-8") for p in sorted(parts_dir.glob("*"))) if parts_dir.is_dir() else ""
    assert "design Step 3 codex-review" in combined


def test_review_append_outer_meta_writes_site(tmp_path: Path) -> None:
    prompt_sidecar = tmp_path / "out.txt.prompt"
    _ = prompt_sidecar.write_text("p", encoding="utf-8")
    meta = tmp_path / "out.txt.meta"
    agents._review_append_outer_meta(meta, prompt_sidecar=prompt_sidecar, risk="high", stderr_sink="", site="design Step 3")  # pylint: disable=protected-access
    assert "OUTER_LAUNCHER_SITE=design Step 3" in meta.read_text(encoding="utf-8")
    meta_default = tmp_path / "out2.meta"
    agents._review_append_outer_meta(meta_default, prompt_sidecar=prompt_sidecar, risk="high", stderr_sink="")  # pylint: disable=protected-access
    assert "OUTER_LAUNCHER_SITE=review Step 2" in meta_default.read_text(encoding="utf-8")


def test_review_cursor_has_structured_findings_blocks_normalization() -> None:
    record = json.dumps(
        {
            "schema_version": 1,
            "scope": "in_scope",
            "severity": "important",
            "focus_area": "correctness",
            "location": "x",
            "what": "y",
            "scenario_or_breakage": "z",
            "suggested_fix": "w",
        }
    )
    text = "Some prose.\n" + record + '\n{"no_issues_found": true}\n'
    assert agents._review_cursor_has_structured_findings(text) is True  # pylint: disable=protected-access
    assert agents._review_cursor_normalize_no_issues(text) == text  # pylint: disable=protected-access
    assert agents._review_cursor_has_structured_findings('{"schema_version": 1}\n') is True  # pylint: disable=protected-access
    prose_then_sentinel = 'All good.\n{"no_issues_found": true}\n'
    assert agents._review_cursor_has_structured_findings(prose_then_sentinel) is False  # pylint: disable=protected-access
    assert agents._review_cursor_normalize_no_issues(prose_then_sentinel) == '{"no_issues_found": true}\n'  # pylint: disable=protected-access


def test_append_implement_launch_failure_composes_sidecar_and_regenerates_tail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "codex-impl.txt"
    sidecar = tmp_path / "codex-impl.log"
    diag = output.with_suffix(output.suffix + ".diag")
    tail = output.with_suffix(output.suffix + ".stderr-tail")
    _ = diag.write_text("generic failure\n", encoding="utf-8")
    _ = sidecar.write_text("launcher stderr detail\n", encoding="utf-8")
    agents._write_stderr_tail(source=diag, output=output)  # pylint: disable=protected-access
    assert "generic failure" in tail.read_text(encoding="utf-8")

    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    def fake_run(_argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    agents._append_implement_launch_failure(tool="codex", output=output, sidecar=sidecar, launcher_exit=1)  # pylint: disable=protected-access
    failure_diag = output.with_suffix(output.suffix + ".failure-diag")
    assert "launcher stderr detail" in failure_diag.read_text(encoding="utf-8")
    assert "launcher stderr detail" in tail.read_text(encoding="utf-8")


def test_append_implement_launch_failure_merges_sidecar_into_existing_failure_diag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "codex-impl.txt"
    sidecar = tmp_path / "codex-impl.log"
    failure_diag = output.with_suffix(output.suffix + ".failure-diag")
    diag = output.with_suffix(output.suffix + ".diag")
    _ = diag.write_text("generic failure\n", encoding="utf-8")
    _ = failure_diag.write_text("===== diag =====\ngeneric failure\n", encoding="utf-8")
    _ = sidecar.write_text("launcher stderr detail\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    def fake_run(_argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    agents._append_implement_launch_failure(tool="codex", output=output, sidecar=sidecar, launcher_exit=1)  # pylint: disable=protected-access
    assert "launcher stderr detail" in failure_diag.read_text(encoding="utf-8")


def test_append_implement_launch_failure_uses_retry_failure_diag_and_auth_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "codex-impl.txt"
    sidecar = tmp_path / "codex-impl.log"
    retry_diag = tmp_path / "codex-impl-retry.txt.failure-diag"
    _ = retry_diag.write_text("not logged in\n", encoding="utf-8")
    _ = sidecar.write_text("", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    captured: dict[str, str] = {}

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if "append-failure" in argv:
            captured["source"] = argv[argv.index("--output-file") + 1]
            captured["verdict"] = argv[argv.index("--verdict") + 1]
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    agents._append_implement_launch_failure(tool="codex", output=output, sidecar=sidecar, launcher_exit=1)  # pylint: disable=protected-access
    assert Path(captured["source"]) == retry_diag
    assert captured["verdict"] == "auth-retries-exhausted"
    tail = output.with_suffix(output.suffix + ".stderr-tail")
    assert "not logged in" in tail.read_text(encoding="utf-8")


def test_append_implement_launch_failure_uses_descriptive_site_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Issue #4911 item 1: /implement Step 2 implement-launch failures must carry a
    # descriptive, caller-consistent site label ("implement Step 2") at both the
    # run-log append-failure call and the vendor-failure-diagnostics part — parity
    # with the reviewer-launch logger's "review Step 2". The logger is
    # tool-parameterized, so Codex and Cursor share the label.
    output = tmp_path / "codex-impl.txt"
    sidecar = tmp_path / "codex-impl.log"
    _ = sidecar.write_text("launcher stderr detail\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    captured: dict[str, str] = {}

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        a = [str(x) for x in argv]
        if "append-failure" in a:
            captured["site"] = a[a.index("--site") + 1]
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    parts_dir = tmp_path / "vendor-failure-diagnostics.parts"

    agents._append_implement_launch_failure(tool="codex", output=output, sidecar=sidecar, launcher_exit=1)  # pylint: disable=protected-access
    assert captured["site"] == "implement Step 2"
    combined = "".join(p.read_text(encoding="utf-8") for p in sorted(parts_dir.glob("*")))
    assert "implement Step 2 codex-implement" in combined

    cursor_out = tmp_path / "cursor-impl.txt"
    cursor_sidecar = tmp_path / "cursor-impl.log"
    _ = cursor_sidecar.write_text("launcher stderr detail\n", encoding="utf-8")
    agents._append_implement_launch_failure(tool="cursor", output=cursor_out, sidecar=cursor_sidecar, launcher_exit=1)  # pylint: disable=protected-access
    assert captured["site"] == "implement Step 2"
    combined = "".join(p.read_text(encoding="utf-8") for p in sorted(parts_dir.glob("*")))
    assert "implement Step 2 cursor-implement" in combined


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
    rc, rendered, msg = agents._render_context_files(paths=[ctx], roots=[tmp_path])  # pylint: disable=protected-access
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
    assert "Reproduce the failing check locally" in agents._ci_prompt(tool="Codex", args=fix_args)  # pylint: disable=protected-access
    conflict_prompt = agents._ci_prompt(tool="Codex", args=conflict_args)  # pylint: disable=protected-access
    assert "Do not run git add" in conflict_prompt
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


def test_launch_codex_ci_resolves_consumer_workdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_cwd = tmp_path / "plugin-cache"
    consumer_repo = tmp_path / "consumer"
    raw_cwd.mkdir()
    consumer_repo.mkdir()
    output = tmp_path / "codex-ci.out"
    captured: dict[str, object] = {}

    def fake_resolve(cwd: str) -> str:
        assert cwd == str(raw_cwd)
        return str(consumer_repo)

    def fake_prepare(_home: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return 0, ""

    def fake_which(name: str) -> str | None:
        return "/usr/bin/true" if name == "codex" else None

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        captured.update(kwargs)
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text("fixed\n", encoding="utf-8")
        _ = output_path.with_suffix(output_path.suffix + ".inner.done").write_text("0\n", encoding="utf-8")
        return agents.RunExternalAgentResult(0, output_path)

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(str(arg) for arg in argv), 0, "", "", 0.0)

    monkeypatch.chdir(raw_cwd)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", fake_resolve)
    monkeypatch.setattr(agents.shutil, "which", fake_which)
    monkeypatch.setattr(agents, "_prepare_codex_home", fake_prepare)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)
    monkeypatch.setattr(agents, "_append_ci_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_emit_ci_launcher_result", lambda *_args, **_kwargs: None)

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
    cmd = list(captured["cmd"])
    assert captured["cwd"] == str(consumer_repo)
    assert cmd[cmd.index("-C") + 1] == str(consumer_repo)
    assert cmd[cmd.index("--add-dir") + 1] == str(consumer_repo)
    assert agents._trust_config_arg(str(consumer_repo)) in cmd
    meta = output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert f"OUTER_LAUNCHER_WORKDIR={consumer_repo}" in meta


def test_launch_codex_ci_finalize_order_and_token_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "codex-ci.out"
    paths = agents.LauncherPaths.from_output(output)
    order: list[str] = []
    original_write = agents._write  # pylint: disable=protected-access
    original_append = agents._append  # pylint: disable=protected-access
    original_promote = agents._promote_inner_done  # pylint: disable=protected-access

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text("partial\n", encoding="utf-8")
        _ = agents.LauncherPaths.from_output(output_path).inner_done.write_text(f"{config.EXIT_TIMEOUT}\n", encoding="utf-8")
        return agents.RunExternalAgentResult(config.EXIT_TIMEOUT, output_path)

    def fake_write(path: str | Path, text: str) -> None:
        path_obj = Path(path)
        if path_obj == paths.stall_json:
            order.append("stall")
        original_write(path=path_obj, text=text)

    def fake_append(path: str | Path, text: str) -> None:
        path_obj = Path(path)
        if path_obj == paths.meta:
            order.append("meta")
        original_append(path=path_obj, text=text)

    def fake_mirror(**_kwargs: object) -> None:
        order.append("events")

    def fake_record_timing(**_kwargs: object) -> None:
        order.append("timing")

    def fake_record_usage(events: Path, sidecar: Path, label: str, token_record: Path | None = None, *, model: str = "") -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        _ = model
        order.append("usage")
        assert token_record == paths.token_record
        _ = paths.token_record.write_text("TOKEN=1\n", encoding="utf-8")

    def fake_emit_kv(key: str, value: str | int) -> None:
        if key == "TOKEN_RECORD":
            order.append("token")
        logging_util.emit_kv(key, str(value))

    def fake_promote(path: Path) -> None:
        order.append("promote")
        original_promote(path)

    def fake_append_failure(*_args: object, **_kwargs: object) -> None:
        order.append("failure")

    def fake_emit_result(output: Path, launcher_exit: int, *, tool: str) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        assert tool == "codex"
        order.append("emit")
        logging_util.emit_kv("LAUNCHER_EXIT", str(config.EXIT_TIMEOUT))
        logging_util.emit_kv("OUTPUT", str(output))

    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/true" if name == "codex" else None)
    monkeypatch.setattr(agents, "_prepare_codex_home", lambda _home, **_kwargs: (0, ""))
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents, "_write", fake_write)
    monkeypatch.setattr(agents, "_append", fake_append)
    monkeypatch.setattr(agents, "_mirror_codex_quota_from_events", fake_mirror)
    monkeypatch.setattr(agents, "_record_launch_timing", fake_record_timing)
    monkeypatch.setattr(agents, "_record_usage_from_events", fake_record_usage)
    monkeypatch.setattr(agents, "_emit_kv", fake_emit_kv)
    monkeypatch.setattr(agents, "_promote_inner_done", fake_promote)
    monkeypatch.setattr(agents, "_append_ci_failure", fake_append_failure)
    monkeypatch.setattr(agents, "_emit_ci_launcher_result", fake_emit_result)

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
    assert order == ["events", "timing", "usage", "token", "meta", "stall", "promote", "failure", "emit"]
    stdout = capsys.readouterr().out
    assert stdout.index("TOKEN_RECORD=") < stdout.index("LAUNCHER_EXIT=")


@pytest.mark.parametrize("old_home", [None, "", "preset-codex-home"])
def test_launch_codex_ci_restores_codex_home_after_launcher_exception(
    old_home: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "codex-ci.out"
    if old_home is None:
        monkeypatch.delenv("CODEX_HOME", raising=False)
    else:
        monkeypatch.setenv("CODEX_HOME", old_home)

    def fake_run_external_agent_with_auth_retries(**_kwargs: object) -> agents.RunExternalAgentResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/true" if name == "codex" else None)
    monkeypatch.setattr(agents, "_prepare_codex_home", lambda _home, **_kwargs: (0, ""))
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(tmp_path))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    with pytest.raises(RuntimeError, match="boom"):
        agents.launch_codex_ci_main(
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

    if old_home is None:
        assert "CODEX_HOME" not in agents.os.environ
    else:
        assert agents.os.environ.get("CODEX_HOME") == old_home


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


@pytest.mark.parametrize(("role", "expected_stall"), [("resolve-conflict", "tree:{workdir}"), ("fix", "stdout")])
def test_launch_cursor_ci_resolves_consumer_workdir_and_preserves_fix_stall_channel(
    role: str,
    expected_stall: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_cwd = tmp_path / "plugin-cache"
    consumer_repo = tmp_path / "consumer"
    raw_cwd.mkdir()
    consumer_repo.mkdir()
    output = tmp_path / f"cursor-ci-{role}.out"
    captured: dict[str, object] = {}

    def fake_resolve(cwd: str) -> str:
        assert cwd == str(raw_cwd)
        return str(consumer_repo)

    def fake_which(name: str) -> str | None:
        return "/usr/bin/true" if name == "cursor" else None

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        captured.update(kwargs)
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text('{"result":"fixed"}\n', encoding="utf-8")
        _ = output_path.with_suffix(output_path.suffix + ".inner.done").write_text("0\n", encoding="utf-8")
        return agents.RunExternalAgentResult(0, output_path)

    def fake_proc_run(argv: Sequence[str], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(str(arg) for arg in argv), 0, "", "", 0.0)

    monkeypatch.chdir(raw_cwd)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", fake_resolve)
    monkeypatch.setattr(agents.shutil, "which", fake_which)
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)
    monkeypatch.setattr(agents, "_append_ci_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agents, "_emit_ci_launcher_result", lambda *_args, **_kwargs: None)

    rc = agents.launch_cursor_ci_main(
        [
            "--role",
            role,
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
    cmd = list(captured["cmd"])
    assert cmd[cmd.index("--workspace") + 1] == str(consumer_repo)
    assert captured["stall_channel"] == expected_stall.format(workdir=consumer_repo)
    meta = output.with_suffix(output.suffix + ".meta").read_text(encoding="utf-8")
    assert f"OUTER_LAUNCHER_WORKDIR={consumer_repo}" in meta


def test_launch_cursor_ci_finalize_order_and_stall_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_cwd = tmp_path / "plugin-cache"
    consumer_repo = tmp_path / "consumer"
    raw_cwd.mkdir()
    consumer_repo.mkdir()
    output = tmp_path / "cursor-ci.out"
    paths = agents.LauncherPaths.from_output(output)
    order: list[str] = []
    original_write = agents._write  # pylint: disable=protected-access
    original_append = agents._append  # pylint: disable=protected-access
    original_promote = agents._promote_inner_done  # pylint: disable=protected-access

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text('{"result":"fixed"}\n', encoding="utf-8")
        _ = agents.LauncherPaths.from_output(output_path).inner_done.write_text(f"{config.EXIT_TIMEOUT}\n", encoding="utf-8")
        return agents.RunExternalAgentResult(config.EXIT_TIMEOUT, output_path)

    def fake_write(path: str | Path, text: str) -> None:
        path_obj = Path(path)
        if path_obj == paths.stall_json:
            order.append("stall")
        original_write(path=path_obj, text=text)

    def fake_append(path: str | Path, text: str) -> None:
        path_obj = Path(path)
        if path_obj == paths.meta:
            order.append("meta")
        original_append(path=path_obj, text=text)

    def fake_record_timing(**_kwargs: object) -> None:
        order.append("timing")

    def fake_record_usage(**_kwargs: object) -> None:
        order.append("usage")
        _ = paths.token_record.write_text("TOKEN=1\n", encoding="utf-8")

    def fake_emit_kv(key: str, value: str | int) -> None:
        if key == "TOKEN_RECORD":
            order.append("token")
        logging_util.emit_kv(key, str(value))

    def fake_promote(path: Path) -> None:
        order.append("promote")
        original_promote(path)

    def fake_append_failure(*_args: object, **_kwargs: object) -> None:
        order.append("failure")

    def fake_emit_result(output: Path, launcher_exit: int, *, tool: str) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        assert tool == "cursor"
        order.append("emit")

    monkeypatch.chdir(raw_cwd)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(consumer_repo))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/true" if name == "cursor" else None)
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents, "_write", fake_write)
    monkeypatch.setattr(agents, "_append", fake_append)
    monkeypatch.setattr(agents, "_record_launch_timing", fake_record_timing)
    monkeypatch.setattr(agents, "_record_cursor_usage_from_output", fake_record_usage)
    monkeypatch.setattr(agents, "_emit_kv", fake_emit_kv)
    monkeypatch.setattr(agents, "_promote_inner_done", fake_promote)
    monkeypatch.setattr(agents, "_append_ci_failure", fake_append_failure)
    monkeypatch.setattr(agents, "_emit_ci_launcher_result", fake_emit_result)

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
    assert order == ["meta", "timing", "usage", "token", "stall", "promote", "failure", "emit"]

    order.clear()
    _ = paths.inner_done.write_text(f"{config.EXIT_TIMEOUT}\n", encoding="utf-8")
    _ = paths.stall_json.write_text("already here\n", encoding="utf-8")
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
    assert "stall" not in order
    assert paths.stall_json.read_text(encoding="utf-8") == "already here\n"


@pytest.mark.parametrize("old_cfg", [None, "", "preset-cursor-cfg"])
def test_launch_cursor_ci_restores_config_dir_after_launcher_exception(
    old_cfg: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_cwd = tmp_path / "plugin-cache"
    consumer_repo = tmp_path / "consumer"
    raw_cwd.mkdir()
    consumer_repo.mkdir()
    output = tmp_path / "cursor-ci.out"
    if old_cfg is None:
        monkeypatch.delenv("CURSOR_CONFIG_DIR", raising=False)
    else:
        monkeypatch.setenv("CURSOR_CONFIG_DIR", old_cfg)

    captured_cfg: Path | None = None

    def fake_run_external_agent_with_auth_retries(**_kwargs: object) -> agents.RunExternalAgentResult:
        nonlocal captured_cfg
        raw = agents.os.environ.get("CURSOR_CONFIG_DIR")
        assert raw is not None
        captured_cfg = Path(raw)
        assert captured_cfg.is_dir()
        raise RuntimeError("boom")

    monkeypatch.chdir(raw_cwd)
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(consumer_repo))
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/true" if name == "cursor" else None)
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)

    with pytest.raises(RuntimeError, match="boom"):
        agents.launch_cursor_ci_main(
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

    assert captured_cfg is not None
    assert not captured_cfg.exists()
    if old_cfg is None:
        assert "CURSOR_CONFIG_DIR" not in agents.os.environ
    else:
        assert agents.os.environ.get("CURSOR_CONFIG_DIR") == old_cfg


def test_launch_codex_implement_finalize_order_uses_explicit_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "session"
    session.mkdir()
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.md"
    agent_prompt = tmp_path / "agent.md"
    _ = plan.write_text("plan\n", encoding="utf-8")
    _ = feature.write_text("feature\n", encoding="utf-8")
    _ = agent_prompt.write_text("---\nname: test\n---\nbody\n", encoding="utf-8")
    output = session / "codex-impl.out"
    sidecar = tmp_path / "codex-impl.log"
    paths = agents.LauncherPaths.from_output(output)
    home = tmp_path / "codex-home"
    order: list[str] = []
    original_append = agents._append  # pylint: disable=protected-access
    original_promote = agents._promote_inner_done  # pylint: disable=protected-access

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        assert kwargs["stderr_path"] == sidecar
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text("transcript\n", encoding="utf-8")
        _ = agents.LauncherPaths.from_output(output_path).inner_done.write_text("4\n", encoding="utf-8")
        return agents.RunExternalAgentResult(4, output_path)

    def fake_append(path: str | Path, text: str) -> None:
        path_obj = Path(path)
        if path_obj == paths.meta:
            order.append("meta")
        original_append(path=path_obj, text=text)

    def fake_mirror(**_kwargs: object) -> None:
        order.append("events")

    def fake_record_timing(**_kwargs: object) -> None:
        order.append("timing")

    def fake_record_usage(events: Path, sidecar: Path, label: str, token_record: Path | None = None, *, model: str = "") -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        _ = token_record
        _ = model
        order.append("usage")

    def fake_append_failure(**kwargs: object) -> None:  # type: ignore[reportAny]
        retry_count = kwargs.get("retry_count", 0)
        _ = retry_count
        sidecar_arg = kwargs.get("sidecar")
        assert sidecar_arg == sidecar
        assert sidecar_arg != paths.sidecar
        order.append("failure")

    def fake_promote(path: Path) -> None:
        order.append("promote")
        original_promote(path)

    def fake_emit(**_kwargs: object) -> None:
        order.append("emit")

    def fake_safe_home() -> Path:
        home.mkdir()
        return home

    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/true" if name == "codex" else None)
    monkeypatch.setattr(agents, "_safe_codex_home_dir", fake_safe_home)
    monkeypatch.setattr(agents, "_prepare_codex_home", lambda _home, **_kwargs: (0, ""))
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(tmp_path))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents, "_append", fake_append)
    monkeypatch.setattr(agents, "_mirror_codex_quota_from_events", fake_mirror)
    monkeypatch.setattr(agents, "_record_implement_timing", fake_record_timing)
    monkeypatch.setattr(agents, "_record_usage_from_events", fake_record_usage)
    monkeypatch.setattr(agents, "_append_implement_launch_failure", fake_append_failure)
    monkeypatch.setattr(agents, "_promote_inner_done", fake_promote)
    monkeypatch.setattr(agents, "_emit_implement_launcher_envelope", fake_emit)
    monkeypatch.setattr(agents.proc, "run", lambda argv, **_kwargs: CommandResult(tuple(str(arg) for arg in argv), 0, "", "", 0.0))

    rc = agents.launch_codex_implement_main(
        [
            "--transcript-path",
            str(output),
            "--sidecar-log",
            str(sidecar),
            "--manifest-path",
            str(session / "manifest.json"),
            "--qa-pending-path",
            str(session / "qa-pending.json"),
            "--scout-manifest-path",
            str(session / "scout.json"),
            "--plan-file",
            str(plan),
            "--feature-file",
            str(feature),
            "--agent-prompt",
            str(agent_prompt),
            "--timeout",
            "5",
        ],
    )

    assert rc == 0
    assert order == ["events", "timing", "usage", "meta", "failure", "promote", "emit"]


def test_launch_cursor_implement_finalize_order_uses_explicit_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = tmp_path / "session"
    session.mkdir()
    plan = tmp_path / "plan.md"
    feature = tmp_path / "feature.md"
    agent_prompt = tmp_path / "agent.md"
    _ = plan.write_text("plan\n", encoding="utf-8")
    _ = feature.write_text("feature\n", encoding="utf-8")
    _ = agent_prompt.write_text("body\n", encoding="utf-8")
    output = session / "cursor-impl.out"
    sidecar = tmp_path / "cursor-impl.log"
    paths = agents.LauncherPaths.from_output(output)
    order: list[str] = []
    original_append = agents._append  # pylint: disable=protected-access
    original_promote = agents._promote_inner_done  # pylint: disable=protected-access

    def fake_run_external_agent_with_auth_retries(**kwargs: object) -> agents.RunExternalAgentResult:
        output_path = kwargs["output"]
        assert isinstance(output_path, Path)
        _ = output_path.write_text('{"usage":{}}\n', encoding="utf-8")
        _ = agents.LauncherPaths.from_output(output_path).inner_done.write_text("5\n", encoding="utf-8")
        return agents.RunExternalAgentResult(5, output_path)

    def fake_append(path: str | Path, text: str) -> None:
        path_obj = Path(path)
        if path_obj == paths.meta:
            order.append("meta")
        original_append(path=path_obj, text=text)

    def fake_record_timing(**_kwargs: object) -> None:
        order.append("timing")

    def fake_record_usage(*_args: object, **_kwargs: object) -> None:
        order.append("usage")

    def fake_append_failure(**kwargs: object) -> None:  # type: ignore[reportAny]
        retry_count = kwargs.get("retry_count", 0)
        _ = retry_count
        sidecar_arg = kwargs.get("sidecar")
        assert sidecar_arg == sidecar
        assert sidecar_arg != paths.sidecar
        order.append("failure")

    def fake_promote(path: Path) -> None:
        order.append("promote")
        original_promote(path)

    def fake_emit(**_kwargs: object) -> None:
        order.append("emit")

    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/usr/bin/true" if name == "cursor" else None)
    monkeypatch.setattr(agents, "cursor_auth_preflight", lambda **_kwargs: agents.AuthVerdict(ok=True, rc=0, message=""))
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "resolve_model_args", lambda *_args, **_kwargs: agents.ModelArgResult(()))
    monkeypatch.setattr(agents, "_resolve_review_codex_workdir", lambda _cwd: str(tmp_path))
    monkeypatch.setattr(agents, "_run_external_agent_with_auth_retries", fake_run_external_agent_with_auth_retries)
    monkeypatch.setattr(agents, "_append", fake_append)
    monkeypatch.setattr(agents, "_record_implement_timing", fake_record_timing)
    monkeypatch.setattr(agents, "_record_cursor_implement_usage", fake_record_usage)
    monkeypatch.setattr(agents, "_append_implement_launch_failure", fake_append_failure)
    monkeypatch.setattr(agents, "_promote_inner_done", fake_promote)
    monkeypatch.setattr(agents, "_emit_implement_launcher_envelope", fake_emit)
    monkeypatch.setattr(agents.proc, "run", lambda argv, **_kwargs: CommandResult(tuple(str(arg) for arg in argv), 0, "", "", 0.0))

    rc = agents.launch_cursor_implement_main(
        [
            "--transcript-path",
            str(output),
            "--sidecar-log",
            str(sidecar),
            "--manifest-path",
            str(session / "manifest.json"),
            "--qa-pending-path",
            str(session / "qa-pending.json"),
            "--scout-manifest-path",
            str(session / "scout.json"),
            "--plan-file",
            str(plan),
            "--feature-file",
            str(feature),
            "--agent-prompt",
            str(agent_prompt),
            "--timeout",
            "5",
        ],
    )

    assert rc == 0
    assert order == ["meta", "timing", "usage", "failure", "promote", "emit"]


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
    rc, rendered, msg = agents._render_context_files(paths=[ctx], roots=[root])  # pylint: disable=protected-access
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier=tiers[0])
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
        tiers=tiers,
        launch_fn=launch_fn,
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier=tiers[0])
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier="codex")
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier=tiers[0])
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier="claude")
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier=tiers[0])
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

    result = agents.run_waterfall(tiers=tiers, launch_fn=launch_fn, first_tier=tiers[0])
    assert result.winning_tier == tiers[-1]
    assert len(calls) == len(tiers)
    assert result.short_circuited is False


def test_launch_claude_ci_uses_opus_default_and_write_capable_argv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    argv_log = tmp_path / "argv.log"
    _ = claude.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$@\" > \"$CLAUDE_ARGV_LOG\"\n"
        "cat >/dev/null\n"
        "printf '%s\\n' '{\"result\":\"fixed\"}'\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{agents.os.environ.get('PATH', '')}")
    monkeypatch.setenv("CLAUDE_ARGV_LOG", str(argv_log))
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
    argv = argv_log.read_text(encoding="utf-8").splitlines()
    assert "-p" in argv
    assert config.CLAUDE_CI_FIX_MODEL in argv
    assert "Read,Edit,Write" in argv
    assert "You are using Claude" not in argv


def test_launch_claude_lint_fix_uses_stdin_and_write_capable_argv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    argv_log = tmp_path / "argv.log"
    stdin_log = tmp_path / "stdin.log"
    prompt_file = tmp_path / "prompt-body.txt"
    _ = prompt_file.write_text("lint failure details\n", encoding="utf-8")
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
    output = tmp_path / "claude-lint-fix.out"
    rc = agents.launch_claude_lint_fix_main(
        [
            "--prompt-body-file",
            str(prompt_file),
            "--output",
            str(output),
            "--timeout",
            "5",
        ],
    )
    assert rc == 0
    argv = argv_log.read_text(encoding="utf-8").splitlines()
    assert "-p" in argv
    assert config.CLAUDE_CI_FIX_MODEL in argv
    assert "Read,Edit,Write" in argv
    assert "lint failure details" not in argv
    assert "lint failure details" in stdin_log.read_text(encoding="utf-8")
    assert output.read_text(encoding="utf-8") == "fixed"


def test_classify_success_expected_output() -> None:
    assert agents.classify_launch_failure(launcher_exit=0) == agents.LaunchFailure("none", "")


def test_no_deleted_launcher_script_skipif_guards() -> None:
    text = Path(__file__).read_text(encoding="utf-8")
    forbidden = (
        "lib-external" + "-launcher-common",
        "launch-codex" + "-drafter",
        "launch-claude" + "-drafter",
        "lib-failed-agent" + "-stderr-tail",
        "lib-cursor" + "-auth",
        "parse-drafter" + "-output",
        "skip" + "if(not " + "LIB" + "_COMMON.is_file()",
    )
    for needle in forbidden:
        assert needle not in text


def test_parse_drafter_output_writes_plan_summary_and_scout(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    plan = tmp_path / "plan.txt.tmp"
    summary = tmp_path / "summary.md.tmp"
    scout = tmp_path / "scout.json.tmp"
    _ = raw.write_text(
        "LARCH_SUMMARY_BEGIN\nsummary\nLARCH_SUMMARY_END\n"
        "LARCH_PLAN_BEGIN\nDo work\ndiff_lines: 7\nLARCH_PLAN_END\n"
        'LARCH_SCOUT_BEGIN\n{"archetypes":[]}\nLARCH_SCOUT_END\n',
        encoding="utf-8",
    )
    result = agents.parse_drafter_output(raw_file=raw, plan_tmp=plan, summary_tmp=summary, scout_tmp=scout)
    assert result == agents.DrafterParseResult(
        plan_lines=2,
        diff_lines=7,
        summary_written=True,
        scout_candidate_written=True,
        scout_fail_reason="",
    )
    assert plan.read_text(encoding="utf-8") == "Do work\ndiff_lines: 7\n"
    assert summary.read_text(encoding="utf-8") == "summary\n"
    assert json.loads(scout.read_text(encoding="utf-8")) == {"archetypes": []}


def test_parse_drafter_output_missing_scout_block_sets_absent_reason(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    plan = tmp_path / "plan.txt.tmp"
    summary = tmp_path / "summary.md.tmp"
    scout = tmp_path / "scout.json.tmp"
    _ = raw.write_text("LARCH_PLAN_BEGIN\nDo work\ndiff_lines: 7\nLARCH_PLAN_END\n", encoding="utf-8")
    result = agents.parse_drafter_output(raw_file=raw, plan_tmp=plan, summary_tmp=summary, scout_tmp=scout)
    assert result.scout_candidate_written is False
    assert result.scout_fail_reason == "absent"
    assert not scout.exists()


@pytest.mark.parametrize(
    "raw_text",
    [
        "LARCH_SCOUT_BEGIN\n{}\nLARCH_SCOUT_END\nLARCH_PLAN_BEGIN\nPlan\ndiff_lines: 1\nLARCH_PLAN_END\n",
        "LARCH_PLAN_BEGIN\nPlan without trailer\nLARCH_PLAN_END\n",
        'LARCH_PLAN_BEGIN\n{"archetypes":[]}\ndiff_lines: 1\nLARCH_PLAN_END\n',
    ],
)
def test_parse_drafter_output_rejects_contract_violations(tmp_path: Path, raw_text: str) -> None:
    raw = tmp_path / "raw.txt"
    plan = tmp_path / "plan.txt.tmp"
    summary = tmp_path / "summary.md.tmp"
    scout = tmp_path / "scout.json.tmp"
    _ = raw.write_text(raw_text, encoding="utf-8")
    with pytest.raises(ValueError, match=r"invalid|missing"):
        agents.parse_drafter_output(raw_file=raw, plan_tmp=plan, summary_tmp=summary, scout_tmp=scout)
    assert not scout.exists()


def test_resolve_failure_diagnostic_source_prefers_base_then_retry(tmp_path: Path) -> None:
    output = tmp_path / "agent.txt"
    retry = tmp_path / "agent-retry.txt.failure-diag"
    diag = output.with_suffix(output.suffix + ".diag")
    _ = retry.write_text("retry\n", encoding="utf-8")
    _ = diag.write_text("diag\n", encoding="utf-8")
    assert agents.resolve_failure_diagnostic_source(output) == retry
    base = output.with_suffix(output.suffix + ".failure-diag")
    _ = base.write_text("base\n", encoding="utf-8")
    assert agents.resolve_failure_diagnostic_source(output) == base


def test_launch_codex_drafter_uses_exact_exec_args_and_cleans_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    repo = tmp_path / "repo"
    design.mkdir()
    repo.mkdir()
    prompt = design / "prompt.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    output = design / "status.txt"
    _ = output.with_suffix(output.suffix + ".failure-diag").write_text("stale\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_exec(argv: list[str], stdout_path: Path, stderr_path: Path) -> int:
        seen["argv"] = list(argv)
        trusted = Path(argv[argv.index("--trusted-instructions-file") + 1])
        seen["trusted_text"] = trusted.read_text(encoding="utf-8")
        raw = Path(argv[argv.index("--output") + 1])
        _ = raw.write_text("LARCH_PLAN_BEGIN\nCodex plan\ndiff_lines: 4\nLARCH_PLAN_END\n", encoding="utf-8")
        _ = raw.with_suffix(raw.suffix + ".token-record").write_text('{"tokens":1}\n', encoding="utf-8")
        _ = stdout_path.write_text("LAUNCHER_EXIT=0\n", encoding="utf-8")
        _ = stderr_path.write_text("", encoding="utf-8")
        return 0

    def fake_proc_run(cmd: Sequence[str], **kwargs: object) -> agents.CommandResult:
        _ = (cmd, kwargs)
        return agents.CommandResult((), 0, "", "", 0.0)

    monkeypatch.setattr(agents, "_launch_codex_exec_inprocess", fake_exec)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)
    rc = agents.launch_codex_drafter(
        prompt_file=str(prompt),
        output_file=str(output),
        timeout="9",
        design_tmpdir=str(design),
        repo_root=str(repo),
        timing_task_kind="codex-plan-draft",
    )
    assert rc == 0
    trusted = str(seen["trusted_text"])
    assert "STRICT CONSTRAINTS" in trusted
    argv_obj = seen["argv"]
    assert isinstance(argv_obj, list)
    argv = [str(item) for item in argv_obj]
    assert argv == [
        "--output",
        argv[1],
        "--timeout",
        "9",
        "--workdir",
        str(repo.resolve()),
        "--add-dir",
        str(repo.resolve()),
        "--sandbox",
        "read-only",
        "--usage-label",
        "codex_plan_draft",
        "--timing-task-kind",
        "codex-plan-draft",
        "--trusted-instructions-file",
        argv[15],
        "--prompt-file",
        str(prompt.resolve()),
    ]
    assert (design / "plan.txt").read_text(encoding="utf-8") == "Codex plan\ndiff_lines: 4\n"
    status = output.read_text(encoding="utf-8")
    assert "STATUS=OK" in status
    assert "PLAN_WRITTEN=true" in status
    assert "PLAN_LINES=2" in status
    assert output.with_suffix(output.suffix + ".token-record").read_text(encoding="utf-8") == '{"tokens":1}\n'
    assert not output.with_suffix(output.suffix + ".failure-diag").exists()
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "0\n"


def test_launch_codex_drafter_rejects_prompt_symlink(tmp_path: Path) -> None:
    design = tmp_path / "design"
    repo = tmp_path / "repo"
    design.mkdir()
    repo.mkdir()
    target = design / "real-prompt.txt"
    _ = target.write_text("prompt", encoding="utf-8")
    prompt = design / "prompt-link.txt"
    prompt.symlink_to(target)
    output = design / "status.txt"
    rc = agents.launch_codex_drafter(
        prompt_file=str(prompt),
        output_file=str(output),
        timeout="5",
        design_tmpdir=str(design),
        repo_root=str(repo),
    )
    assert rc == 2


def test_launch_codex_drafter_failure_uses_sidecar_for_stderr_tail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    repo = tmp_path / "repo"
    design.mkdir()
    repo.mkdir()
    prompt = design / "prompt.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    output = design / "status.txt"

    def fake_exec(argv: list[str], stdout_path: Path, stderr_path: Path) -> int:
        raw = Path(argv[argv.index("--output") + 1])
        _ = raw.with_suffix(raw.suffix + ".sidecar").write_text("sidecar failure\n", encoding="utf-8")
        _ = stdout_path.write_text("LAUNCHER_EXIT=13\n", encoding="utf-8")
        _ = stderr_path.write_text("stderr fallback\n", encoding="utf-8")
        return 0

    def fake_proc_run(cmd: Sequence[str], **kwargs: object) -> agents.CommandResult:
        _ = (cmd, kwargs)
        return agents.CommandResult((), 0, "", "", 0.0)

    monkeypatch.setattr(agents, "_launch_codex_exec_inprocess", fake_exec)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)
    rc = agents.launch_codex_drafter(
        prompt_file=str(prompt),
        output_file=str(output),
        timeout="5",
        design_tmpdir=str(design),
        repo_root=str(repo),
    )
    assert rc == 13
    assert output.with_suffix(output.suffix + ".failure-diag").read_text(encoding="utf-8") == "CODEX_EXEC_FAILED\n"
    tail = output.with_suffix(output.suffix + ".stderr-tail").read_text(encoding="utf-8")
    assert "sidecar failure" in tail
    assert "stderr fallback" not in tail
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "13\n"


def test_launch_codex_drafter_main_succeeds_when_exec_exit_on_done_under_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    repo = tmp_path / "repo"
    design.mkdir()
    repo.mkdir()
    prompt = design / "prompt.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    output = design / "status.txt"

    logging_util.reset_quiet_state()
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_DESIGN_TMPDIR, str(design))

    def fake_launch_codex_exec_main(argv: list[str] | None = None) -> int:
        argv = list(argv or [])
        raw = Path(argv[argv.index("--output") + 1])
        _ = raw.write_text("LARCH_PLAN_BEGIN\nquiet plan\ndiff_lines: 2\nLARCH_PLAN_END\n", encoding="utf-8")
        _ = raw.with_suffix(raw.suffix + ".token-record").write_text('{"tokens":1}\n', encoding="utf-8")
        _ = raw.with_suffix(raw.suffix + ".done").write_text("0\n", encoding="utf-8")
        agents._emit_kv(key="LAUNCHER_EXIT", value=0)
        agents._emit_kv(key="OUTPUT", value=str(raw))
        return 0

    def fake_proc_run(cmd: Sequence[str], **kwargs: object) -> agents.CommandResult:
        _ = (cmd, kwargs)
        return agents.CommandResult((), 0, "", "", 0.0)

    monkeypatch.setattr(agents, "launch_codex_exec_main", fake_launch_codex_exec_main)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)

    read_fd, write_fd = os.pipe()
    backup_fd3: int | None = None
    with contextlib.suppress(OSError):
        backup_fd3 = os.dup(3)
    try:
        _ = os.dup2(write_fd, 3)
        os.close(write_fd)
        monkeypatch.setenv(config.ENV_LARCH_QUIET_ACTIVE, "1")
        monkeypatch.setenv(config.ENV_LARCH_QUIET_PID, str(os.getpid()))
        rc = agents.launch_codex_drafter_main(
            [
                "--prompt-file",
                str(prompt),
                "--output-file",
                str(output),
                "--timeout",
                "9",
                "--design-tmpdir",
                str(design),
                "--repo-root",
                str(repo),
                "--timing-task-kind",
                "codex-plan-draft",
            ],
        )
        contract = os.read(read_fd, 4096).decode("utf-8")
    finally:
        if backup_fd3 is not None:
            _ = os.dup2(backup_fd3, 3)
            os.close(backup_fd3)
        else:
            with contextlib.suppress(OSError):
                os.close(3)
        os.close(read_fd)
        logging_util.reset_quiet_state()

    assert rc == 0
    assert "STATUS=OK" in output.read_text(encoding="utf-8")
    assert (design / "plan.txt").read_text(encoding="utf-8") == "quiet plan\ndiff_lines: 2\n"
    assert "STATUS=OK" in contract


def test_launch_claude_drafter_uses_exact_argv_without_timeout_wrapper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    repo = tmp_path / "repo"
    design.mkdir()
    repo.mkdir()
    prompt = design / "prompt.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    output = design / "status.txt"
    seen: dict[str, object] = {}

    def fake_which(name: str) -> str | None:
        assert name == "timeout"


    class Completed:
        returncode = 0

    def fake_run(cmd: Sequence[str], **kwargs: object) -> Completed:
        seen["cmd"] = list(cmd)
        seen["input"] = kwargs.get("input")
        stdout = kwargs["stdout"]
        stdout.write(
            '{"result":"LARCH_PLAN_BEGIN\\nPlan body\\ndiff_lines: 3\\nLARCH_PLAN_END\\n",'
            '"usage":{"input_tokens":1,"output_tokens":2}}'
        )
        return Completed()

    monkeypatch.setattr(agents.shutil, "which", fake_which)
    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    monkeypatch.setattr(agents.proc, "run", lambda *_args, **_kwargs: agents.CommandResult((), 0, "", "", 0.0))
    rc = agents.launch_claude_drafter(
        model="claude-test",
        prompt_file=str(prompt),
        output_file=str(output),
        timeout="5",
        design_tmpdir=str(design),
        repo_root=str(repo),
    )
    assert rc == 0
    assert seen["cmd"] == [
        "claude",
        "--model",
        "claude-test",
        "--print",
        "--output-format",
        "json",
        "--add-dir",
        str(repo.resolve()),
        "--allowedTools",
        "Read,Glob,Grep,LS",
        "--permission-mode",
        "plan",
    ]
    assert seen["input"] == "prompt body"
    assert (design / "plan.txt").read_text(encoding="utf-8") == "Plan body\ndiff_lines: 3\n"
    assert "PLAN_WRITTEN=true" in output.read_text(encoding="utf-8")


def test_launch_claude_drafter_timeout_wrapper_maps_timeout_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    repo = tmp_path / "repo"
    design.mkdir()
    repo.mkdir()
    prompt = design / "prompt.txt"
    _ = prompt.write_text("prompt body", encoding="utf-8")
    output = design / "status.txt"
    seen: dict[str, object] = {}

    class Completed:
        returncode = config.EXIT_TIMEOUT

    def fake_which(name: str) -> str:
        assert name == "timeout"
        return "/usr/bin/timeout"

    def fake_run(cmd: Sequence[str], **kwargs: object) -> Completed:
        seen["cmd"] = list(cmd)
        seen["timeout_kw"] = kwargs.get("timeout")
        stderr = kwargs["stderr"]
        stderr.write("timed out\n")
        return Completed()

    def fake_proc_run(cmd: Sequence[str], **kwargs: object) -> agents.CommandResult:
        _ = (cmd, kwargs)
        return agents.CommandResult((), 0, "", "", 0.0)

    monkeypatch.setattr(agents.shutil, "which", fake_which)
    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    monkeypatch.setattr(agents.proc, "run", fake_proc_run)
    rc = agents.launch_claude_drafter(
        model="claude-test",
        prompt_file=str(prompt),
        output_file=str(output),
        timeout="5",
        design_tmpdir=str(design),
        repo_root=str(repo),
    )
    assert rc == config.EXIT_TIMEOUT
    cmd_obj = seen["cmd"]
    assert isinstance(cmd_obj, list)
    assert [str(item) for item in cmd_obj[:2]] == ["/usr/bin/timeout", "5"]
    assert seen["timeout_kw"] is None
    status = output.read_text(encoding="utf-8")
    assert "STATUS=TIMEOUT" in status
    assert "DRAFTER_LAUNCHED=true" in status
    assert output.with_suffix(output.suffix + ".stderr-tail").read_text(encoding="utf-8") == "timed out\n"


def test_launch_claude_drafter_main_rejects_wrapper_read_tool_flags() -> None:
    rc = agents.launch_claude_drafter_main(
        [
            "--model",
            "claude-test",
            "--prompt-file",
            "/tmp/prompt.txt",
            "--output-file",
            "/tmp/status.txt",
            "--timeout",
            "5",
            "--design-tmpdir",
            "/tmp",
            "--repo-root",
            "/tmp",
            "--read-tools",
        ]
    )
    assert rc == 2


def test_status_check_emits_contract_keys(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(agents, "_read_plugin_version_best_effort", lambda: "1.2.3")
    monkeypatch.setattr(
        agents,
        "check_reviewers",
        lambda: agents.CheckReviewersResult(
            codex_binary_found=True,
            cursor_binary_found=False,
            codex_present=True,
            cursor_present=False,
        ),
    )
    rc = agents.status_check_main([])
    assert rc == 0
    out = capsys.readouterr().out
    for key in (
        "LARCH_PLUGIN_VERSION=1.2.3",
        "CODEX_BINARY_FOUND=true",
        "CURSOR_BINARY_FOUND=false",
        "CODEX_PRESENT=true",
        "CURSOR_PRESENT=false",
        "CODEX_STATE=ok",
        "CURSOR_STATE=binary-missing",
        "DEGRADED=true",
    ):
        assert key in out
    assert "CODING_BINARY_FOUND" not in out


def test_status_check_version_and_probe_fallback(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(agents, "_read_plugin_version_best_effort", lambda: "unknown")

    def raise_probe() -> agents.CheckReviewersResult:
        raise RuntimeError("probe failed")

    monkeypatch.setattr(agents, "check_reviewers", raise_probe)
    assert agents.status_check_main([]) == 0
    out = capsys.readouterr().out
    assert "LARCH_PLUGIN_VERSION=unknown" in out
    assert "CODEX_STATE=binary-missing" in out
    assert "CURSOR_STATE=binary-missing" in out
    assert "DEGRADED=true" in out


def test_review_specialist_render_args_nested_implement_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    session_env = impl / "session-env.sh"
    session_env.write_text("IMPLEMENT_TMPDIR=" + str(impl) + "\n", encoding="utf-8")
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    args = argparse.Namespace(
        agent_file=str(tmp_path / "agent.md"),
        mode="diff",
        description_text="",
        scope_files="",
        competition_notice_file="",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        competition_notice=False,
        output=str(round_dir / "codex-specialist-correctness-output.txt"),
        session_env_path=str(session_env),
    )
    render_args = agents._review_specialist_render_args(args)
    ledger_idx = render_args.index("--findings-ledger-file")
    assert render_args[ledger_idx + 1] == str(impl / "findings-ledger.tsv")
    assert render_args[render_args.index("--session-env-path") + 1] == str(session_env)


def test_codex_role_model_resolution_ignores_default_model_and_global_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_MODEL", "strong-global")
    monkeypatch.delenv("LARCH_CODEX_REVIEW_MODEL", raising=False)
    monkeypatch.delenv("LARCH_CODEX_VOTE_MODEL", raising=False)
    monkeypatch.delenv("LARCH_CODEX_FIX_MODEL", raising=False)

    assert agents.resolve_model_args("codex", codex_role="review", default_model="custom").argv[:2] == ("-m", "gpt-5.4-mini")
    assert agents.resolve_model_args("codex", codex_role="vote", default_model="custom").argv[:2] == ("-m", "gpt-5.4-mini")
    assert agents.resolve_model_args("codex", codex_role="fix", default_model="custom").argv[:2] == ("-m", "gpt-5.4-mini")


def test_codex_default_role_preserves_default_model_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LARCH_CODEX_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_CODEX_MODEL", raising=False)

    assert agents.resolve_model_args("codex", codex_role="default", default_model="custom-default").argv[:2] == ("-m", "custom-default")


def test_codex_role_env_rejects_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_REVIEW_MODEL", "   ")

    with pytest.raises(ValueError, match="LARCH_CODEX_REVIEW_MODEL"):
        agents.resolve_model_args("codex", codex_role="review")


def test_codex_role_env_rejects_control_character(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_VOTE_MODEL", "mini\nbad")

    with pytest.raises(ValueError, match="LARCH_CODEX_VOTE_MODEL"):
        agents.resolve_model_args("codex", codex_role="vote")


def test_model_args_main_codex_role_ignores_default_and_global_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_CODEX_MODEL", "strong-global")
    monkeypatch.delenv("LARCH_CODEX_REVIEW_MODEL", raising=False)

    rc = agents.model_args_main(["--tool", "codex", "--codex-role", "review", "--default-model", "custom"])

    assert rc == 0
    assert capsys.readouterr().out.splitlines()[:2] == ["-m", "gpt-5.4-mini"]


def test_codex_probe_blank_review_model_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LARCH_CODEX_REVIEW_MODEL", "   ")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(agents, "_prepare_codex_home", lambda *_args, **_kwargs: (0, ""))

    assert agents._run_one_codex_probe(1) == agents._PROBE_NO_RETRY_RC  # pylint: disable=protected-access


def test_parse_drafter_output_extracts_dialectic_without_promoting(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    plan = tmp_path / "plan.tmp"
    summary = tmp_path / "summary.tmp"
    scout = tmp_path / "scout.tmp"
    raw.write_text(
        "LARCH_PLAN_BEGIN\n## Plan\n\ndiff_lines: 1\nLARCH_PLAN_END\n"
        "LARCH_DIALECTIC_BEGIN\n"
        '{"decisions":[{"id":"fork","title":"Fork","option_a":"A","option_b":"B","tradeoff":"real tradeoff","drafter_pick":"option_a","why_this_matters":"important"}]}\n'
        "LARCH_DIALECTIC_END\n"
        'LARCH_SCOUT_BEGIN\n{"archetypes":[]}\nLARCH_SCOUT_END\n',
        encoding="utf-8",
    )
    parsed = agents.parse_drafter_output(raw_file=raw, plan_tmp=plan, summary_tmp=summary, scout_tmp=scout)
    assert parsed.dialectic_parsed is True
    assert parsed.dialectic_payload
    assert not (tmp_path / "dialectic-clarifier-candidates.json").exists()


def test_parse_drafter_output_malformed_dialectic_keeps_plan(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    plan = tmp_path / "plan.tmp"
    summary = tmp_path / "summary.tmp"
    raw.write_text(
        "LARCH_PLAN_BEGIN\n## Plan\n\ndiff_lines: 1\nLARCH_PLAN_END\n"
        "LARCH_DIALECTIC_BEGIN\n{bad\nLARCH_DIALECTIC_END\n",
        encoding="utf-8",
    )
    parsed = agents.parse_drafter_output(raw_file=raw, plan_tmp=plan, summary_tmp=summary)
    assert parsed.dialectic_parsed is False
    assert parsed.dialectic_fail_reason == "invalid_dialectic_json"
    assert plan.read_text(encoding="utf-8").endswith("diff_lines: 1\n")


def test_parse_drafter_output_dialectic_inside_plan_is_fatal(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "LARCH_PLAN_BEGIN\n## Plan\nLARCH_DIALECTIC_BEGIN\n{}\nLARCH_DIALECTIC_END\ndiff_lines: 1\nLARCH_PLAN_END\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dialectic block may not appear inside plan"):
        agents.parse_drafter_output(raw_file=raw, plan_tmp=tmp_path / "plan.tmp", summary_tmp=tmp_path / "summary.tmp")
