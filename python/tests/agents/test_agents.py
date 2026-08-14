# pyright: reportPrivateUsage=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportArgumentType=false
"""Tests for agents.py classification and waterfall."""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.agents import agents
from larch.core import config
from larch.agents.agents import LaunchFailure, TierAttempt
from larch.agents import _run_external
from larch.agents import _auth
from larch.agents import _failure_diag
from larch.agents import _launch_failure
from larch.agents import _types
from test_support import completed, ok

if TYPE_CHECKING:
    from larch.core.proc import CommandResult

USAGE_MISSING_DIAGNOSTIC = "agent parse-codex-usage: no usage events\n"
REPO_ROOT = Path(__file__).resolve().parents[3]


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
        return ok(call)


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
    assert not [call for call in runner.calls if call[2:4] == ("token", "append-record")]
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
    ("launcher_exit", "tool", "diagnostic", "reason"),
    [
        (
            7,
            "codex",
            "stream disconnected before completion: error sending request for url (https://api.openai.com/v1/responses)",
            config.LAUNCH_FAILURE_REASON_OPENAI_STREAM_DISCONNECTED,
        ),
        (
            8,
            "cursor",
            "Failed to reach the Cursor API. If you are behind a corporate proxy, set HTTPS_PROXY.",
            config.LAUNCH_FAILURE_REASON_CURSOR_API_UNREACHABLE,
        ),
    ],
)
def test_classify_known_vendor_connectivity_failures(
    tmp_path: Path, launcher_exit: int, tool: str, diagnostic: str, reason: str
) -> None:
    sidecar = tmp_path / "failure-diag.log"
    _ = sidecar.write_text(diagnostic, encoding="utf-8")

    failure = agents.classify_launch_failure(
        launcher_exit=launcher_exit,
        sidecar=sidecar,
        tool=tool,
        output_file=tmp_path / "output.txt",
    )

    assert failure == LaunchFailure("health", reason)


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
    assert argv[0].endswith("scripts/larch.sh")
    assert argv[1] == "agent"
    assert argv[2] == f"launch-{tier}-ci"
    assert "--role" in argv


def test_model_args_defaults_and_effort() -> None:
    result = agents.resolve_model_args("codex", with_effort=True)
    assert result.argv[:2] == ("-m", "gpt-5.6-sol")
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


def test_resolve_cursor_model_honors_caller_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_LARCH_CURSOR_MODEL, raising=False)
    monkeypatch.delenv(config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, raising=False)

    assert agents.resolve_model_args("cursor", default_model=config.CURSOR_GROK_4_6_HIGH_MODEL).argv == ("--model", config.CURSOR_GROK_4_6_HIGH_MODEL)


def test_resolve_cursor_model_env_override_beats_caller_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_LARCH_CURSOR_MODEL, "cursor-env-override")
    monkeypatch.delenv(config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, raising=False)

    assert agents.resolve_model_args("cursor", default_model=config.CURSOR_GROK_4_6_HIGH_MODEL).argv == ("--model", "cursor-env-override")


def test_resolve_cursor_model_plugin_override_beats_caller_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_LARCH_CURSOR_MODEL, raising=False)
    monkeypatch.setenv(config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, "cursor-plugin-override")

    assert agents.resolve_model_args("cursor", default_model=config.CURSOR_GROK_4_6_HIGH_MODEL).argv == ("--model", "cursor-plugin-override")


def test_resolve_cursor_model_larch_env_wins_over_plugin_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_LARCH_CURSOR_MODEL, "cursor-env-wins")
    monkeypatch.setenv(config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, "cursor-plugin-loses")

    assert agents.resolve_model_args("cursor", default_model=config.CURSOR_GROK_4_6_HIGH_MODEL).argv == ("--model", "cursor-env-wins")


def test_resolve_model_args_ctx_absent_primary_uses_plugin_fallback() -> None:
    from larch.core.ctx import Ctx  # noqa: PLC0415

    ctx = Ctx.from_mapping({config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL: "plugin-model"})
    assert agents.resolve_model_args("codex", ctx=ctx).argv == ("-m", "plugin-model")


def test_resolve_model_args_ctx_empty_primary_rejects_blank() -> None:
    from larch.core.ctx import Ctx  # noqa: PLC0415

    ctx = Ctx.from_mapping({config.ENV_LARCH_CODEX_MODEL: "   "})
    with pytest.raises(ValueError, match="blank"):
        agents.resolve_model_args("codex", ctx=ctx)


def test_resolve_model_args_ctx_primary_wins_over_plugin() -> None:
    from larch.core.ctx import Ctx  # noqa: PLC0415

    ctx = Ctx.from_mapping(
        {
            config.ENV_LARCH_CODEX_MODEL: "primary-model",
            config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL: "plugin-model",
        }
    )
    assert agents.resolve_model_args("codex", ctx=ctx).argv == ("-m", "primary-model")


def test_run_external_agent_inner_sentinel_suffix_ctx_override(tmp_path: Path) -> None:
    from larch.core.ctx import Ctx  # noqa: PLC0415

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


def test_cursor_auth_export_env_sets_no_open_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    # issue #5797: larch must suppress cursor-agent's Cursor.app GUI popup in every
    # cursor lane. cursor_auth_export_env is the shared pre-spawn chokepoint.
    monkeypatch.delenv("NO_OPEN_BROWSER", raising=False)
    agents.cursor_auth_export_env()
    assert agents.os.environ["NO_OPEN_BROWSER"] == "1"


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


def test_run_external_agent_codex_policy_rejection_fast_fails(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    paths = agents.LauncherPaths.from_output(output)
    start = time.monotonic()

    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=30,
        stdout_path=paths.events,
        stderr_path=paths.sidecar,
        cmd=[
            sys.executable,
            "-c",
            (
                "import sys, time; "
                "print('error=exec_command failed for bash: CreateProcess { message: "
                "\"Rejected(\\\\\"blocked by policy\\\\\")\" }', flush=True); "
                "time.sleep(30)"
            ),
        ],
        poll_interval=0.05,
    )

    assert time.monotonic() - start < 5
    assert result.exit_code == 1
    assert paths.done.read_text(encoding="utf-8") == "1\n"
    diag = paths.diag.read_text(encoding="utf-8")
    assert "FAILURE_CLASS=policy-rejection" in diag
    assert "POLICY_REJECTION=true" in diag
    assert "Rejected" in diag
    assert "124" not in paths.done.read_text(encoding="utf-8")
    assert "policy-rejection" in paths.failure_diag.read_text(encoding="utf-8")


def test_run_external_agent_codex_policy_rejection_requires_both_families(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    paths = agents.LauncherPaths.from_output(output)
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=1,
        stdout_path=paths.events,
        stderr_path=paths.sidecar,
        cmd=[
            sys.executable,
            "-c",
            "import time; print('CreateProcess Rejected blocked by policy', flush=True); time.sleep(5)",
        ],
        poll_interval=0.05,
    )

    assert result.exit_code == config.EXIT_TIMEOUT
    diag = paths.diag.read_text(encoding="utf-8")
    assert "FAILURE_CLASS=policy-rejection" not in diag
    assert "POLICY_REJECTION=true" not in diag


def test_run_external_agent_codex_policy_no_false_positive_aggregated_output(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    paths = agents.LauncherPaths.from_output(output)
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=1,
        stdout_path=paths.events,
        stderr_path=paths.sidecar,
        cmd=[
            sys.executable,
            "-c",
            (
                "import json, time; "
                "item = {'type': 'item.completed', 'item': {"
                "'id': 'item_0', 'type': 'command_execution', "
                "'command': 'rg trigger larch-logs', "
                "'aggregated_output': 'exec_command failed for bash: Rejected(blocked by policy)', "
                "'exit_code': 0, 'status': 'completed'}}; "
                "print(json.dumps(item), flush=True); "
                "time.sleep(5)"
            ),
        ],
        poll_interval=0.05,
    )

    assert result.exit_code == config.EXIT_TIMEOUT
    diag = paths.diag.read_text(encoding="utf-8")
    assert "FAILURE_CLASS=policy-rejection" not in diag
    assert "POLICY_REJECTION=true" not in diag


def test_run_external_agent_codex_policy_no_false_positive_truncated_aggregated_output(tmp_path: Path) -> None:
    output = tmp_path / "codex.out"
    paths = agents.LauncherPaths.from_output(output)
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=1,
        stdout_path=paths.events,
        stderr_path=paths.sidecar,
        cmd=[
            sys.executable,
            "-c",
            (
                "import json, time; "
                "payload = 'x' * 40000 + ' exec_command failed for bash: Rejected(blocked by policy)'; "
                "item = {'type': 'item.completed', 'item': {"
                "'id': 'item_0', 'type': 'command_execution', "
                "'command': 'rg trigger larch-logs', "
                "'aggregated_output': payload, "
                "'exit_code': 0, 'status': 'completed'}}; "
                "print(json.dumps(item), flush=True); "
                "time.sleep(5)"
            ),
        ],
        poll_interval=0.05,
    )

    assert result.exit_code == config.EXIT_TIMEOUT
    diag = paths.diag.read_text(encoding="utf-8")
    assert "FAILURE_CLASS=policy-rejection" not in diag
    assert "POLICY_REJECTION=true" not in diag


def test_codex_policy_rejection_excerpt_still_detects_genuine_rejection_after_truncated_command() -> None:
    safe_payload = (
        "x" * (_run_external._CODEX_POLICY_REJECTION_TAIL_BYTES + 128)
        + " exec_command failed for bash: Rejected(blocked by policy)"
    )
    completed_line = json.dumps({
        "type": "item.completed",
        "item": {
            "id": "item_0",
            "type": "command_execution",
            "command": "rg trigger larch-logs",
            "aggregated_output": safe_payload,
            "exit_code": 0,
            "status": "completed",
        },
    })
    genuine_line = 'error=exec_command failed for bash: CreateProcess {"message":"Rejected(blocked by policy)"}'

    assert len(completed_line) > _run_external._CODEX_POLICY_REJECTION_TAIL_BYTES
    assert _run_external._codex_policy_rejection_excerpt(f"{completed_line}\n") == ""

    excerpt = _run_external._codex_policy_rejection_excerpt(f"{completed_line}\n{genuine_line}\n")

    assert "exec_command failed" in excerpt
    assert "Rejected(blocked by policy)" in excerpt


def test_parse_codex_gate_detail_accepts_known_signals_and_rejects_unknown() -> None:
    identity = "codex-review-test"
    expected = _launch_failure.detect_codex_cli_gate(
        "requires a newer version of Codex", fallback_model="gpt-5-codex"
    )
    assert expected is not None

    def payload(signal: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "identity": identity,
            "model": expected.model,
            "signal": signal,
            "message": expected.message,
        }

    for known in (
        _types.CODEX_GATE_SIGNAL_METADATA_NOT_FOUND,
        _types.CODEX_GATE_SIGNAL_NEWER_REQUIRED,
    ):
        parsed = _auth._parse_codex_gate_detail(payload=payload(known), identity=identity)  # pylint: disable=protected-access
        assert parsed is not None
        assert parsed.signal == known

    rejected = _auth._parse_codex_gate_detail(payload=payload("bogus-signal"), identity=identity)  # pylint: disable=protected-access
    assert rejected is None


def test_sanitize_codex_events_for_policy_scan_preserves_failed_command_output() -> None:
    line = json.dumps({
        "type": "item.completed",
        "item": {
            "id": "item_1",
            "type": "command_execution",
            "command": "rg trigger larch-logs",
            "aggregated_output": "exec_command failed for bash: Rejected(blocked by policy)",
            "exit_code": 1,
            "status": "completed",
        },
    })
    sanitized = _run_external._sanitize_codex_events_for_policy_scan(line)
    assert "exec_command failed" in sanitized
    assert "Rejected(blocked by policy)" in sanitized


def test_sanitize_codex_events_for_policy_scan_preserves_in_progress_output() -> None:
    line = json.dumps({
        "type": "item.started",
        "item": {
            "id": "item_2",
            "type": "command_execution",
            "command": "rg trigger larch-logs",
            "aggregated_output": "exec_command failed: Rejected(blocked by policy)",
            "exit_code": None,
            "status": "in_progress",
        },
    })
    sanitized = _run_external._sanitize_codex_events_for_policy_scan(line)
    assert "exec_command failed" in sanitized
    assert "Rejected(blocked by policy)" in sanitized


def test_sanitize_codex_events_for_policy_scan_preserves_missing_exit_code() -> None:
    line = json.dumps({
        "type": "item.completed",
        "item": {
            "id": "item_3",
            "type": "command_execution",
            "command": "rg trigger larch-logs",
            "aggregated_output": "exec_command failed: Rejected(blocked by policy)",
            "status": "completed",
        },
    })
    sanitized = _run_external._sanitize_codex_events_for_policy_scan(line)
    assert "exec_command failed" in sanitized
    assert "Rejected(blocked by policy)" in sanitized


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


def test_compose_failure_diag_dedupes_identical_additional_diagnostics(tmp_path: Path) -> None:
    output = tmp_path / "agent.out"
    _ = output.with_suffix(output.suffix + ".diag").write_text("diag body\n", encoding="utf-8")

    agents._compose_failure_diag(output)  # pylint: disable=protected-access
    agents._compose_failure_diag(output)  # pylint: disable=protected-access

    carrier = output.with_suffix(output.suffix + ".failure-diag").read_text(encoding="utf-8")
    assert carrier.count("===== diag =====") == 1
    assert "===== additional failure diagnostics =====" not in carrier


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

    monkeypatch.setattr(_run_external, "Timer", FakeTimer)
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
    monkeypatch.setenv("LIB_CURSOR_AUTH_TEST_PREREAD_TOKEN", "crsr_from_keychain")
    monkeypatch.setattr(_auth, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(_auth, "external_startup_lock_release_after", fake_release)
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
    monkeypatch.setattr(_auth, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(_auth, "external_startup_lock_release_after", fake_release)
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
    monkeypatch.setattr(_auth, "external_startup_lock_acquire", fake_acquire)
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
    monkeypatch.setattr(_auth, "external_startup_lock_acquire", fake_acquire)
    assert agents.cursor_auth_preflight(caller="test").ok is True
    agents.cursor_preread_service_token()
    assert not calls


def _cursor_auth_unlock(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_acquire(tool: str) -> agents.StartupLockState:
        _ = tool
        return agents.StartupLockState(None)

    def fake_release(state: agents.StartupLockState, delay: float | None = None) -> None:
        _ = (state, delay)

    monkeypatch.delenv("LARCH_LIB_CURSOR_AUTH_TEST_MODE", raising=False)
    monkeypatch.setenv("CURSOR_API_KEY", "")
    monkeypatch.setattr(agents.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(_auth, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(_auth, "external_startup_lock_release_after", fake_release)


def test_cursor_auth_preflight_probes_keychain_readability(monkeypatch: pytest.MonkeyPatch) -> None:
    # #5518: the preflight must READ the token (-w), not just check existence, so it fails
    # closed when an access-controlled entry exists but the -w read is denied (the split-step
    # bug that let Cursor launch without credentials and return a canned, un-reviewed result).
    _cursor_auth_unlock(monkeypatch)
    monkeypatch.setattr(agents.time, "sleep", lambda *_a, **_k: None)
    captured: list[list[str]] = []

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 1)

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    verdict = agents.cursor_auth_preflight(caller="test")
    assert verdict.ok is False
    assert verdict.rc == 2
    assert captured
    assert "-w" in captured[-1]
    assert "find-generic-password" in captured[-1]


def test_cursor_auth_preflight_passes_when_keychain_read_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _cursor_auth_unlock(monkeypatch)

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed(list(argv), "crsr_from_keychain\n")

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    verdict = agents.cursor_auth_preflight(caller="test")
    assert verdict.ok is True
    assert verdict.rc == 0


def test_cursor_preread_surfaces_failed_keychain_read(monkeypatch: pytest.MonkeyPatch) -> None:
    # #5518: when the -w read fails, surface a diagnostic instead of silently leaving
    # CURSOR_API_KEY unset (which lets the Cursor slot auth-fail in-process).
    _cursor_auth_unlock(monkeypatch)
    warnings: list[str] = []
    monkeypatch.setattr(_auth, "_err", warnings.append)

    def fake_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(argv), 1, stdout="")

    monkeypatch.setattr(agents.subprocess, "run", fake_run)
    assert agents.cursor_preread_service_token() is False
    assert not agents.os.environ.get("CURSOR_API_KEY")
    assert warnings
    assert "keychain -w read returned no token" in warnings[0]


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

    monkeypatch.setattr(_run_external, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 2)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", fake_lock)
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", fake_release)
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

    monkeypatch.setattr(_run_external, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 5)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", lambda tool: agents.StartupLockState(None))  # noqa: ARG005
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005
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

    monkeypatch.setattr(_run_external, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 1)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", lambda tool: agents.StartupLockState(None))  # noqa: ARG005
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005
    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="codex",
        output=output,
        timeout_seconds=5,
        cmd=["codex"],
    )
    assert calls["count"] == 2
    assert result.exit_code == 1


def test_policy_rejection_marker_skips_auth_and_empty_retries(
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
        output_path.with_suffix(output_path.suffix + ".diag").write_text(
            "FAILURE_CLASS=policy-rejection\n"
            "POLICY_REJECTION=true\n"
            "authentication failed\n",
            encoding="utf-8",
        )
        return agents.RunExternalAgentResult(1, output_path)

    monkeypatch.setattr(_run_external, "run_external_agent", fake_run_external_agent)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 5)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", lambda tool: agents.StartupLockState(None))  # noqa: ARG005
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005

    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="codex",
        output=output,
        timeout_seconds=5,
        cmd=["codex"],
    )

    assert calls["count"] == 1
    assert result.exit_code == 1
def test_vendor_failure_diagnostics_refuses_symlinked_parts_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "diagnostics.txt"
    _ = source.write_text("failure detail\n", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "vendor-failure-diagnostics.parts").symlink_to(
        target, target_is_directory=True
    )
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    _run_external._append_vendor_failure_diagnostics(  # pylint: disable=protected-access
        source, site="review Step 2 codex-review", exit_code=1
    )

    assert not list(target.iterdir())


def test_read_tail_update_refuses_symlinked_implement_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside-events.jsonl"
    _ = outside.write_text("attacker content\n", encoding="utf-8")
    impl = tmp_path / "implement"
    impl.mkdir()
    watch = impl / "events.jsonl"
    watch.symlink_to(outside)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))

    update = _run_external._read_tail_update(  # pylint: disable=protected-access
        path=watch, offset=0
    )

    assert update.offset == 0
    assert update.text == ""








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


def test_stall_kill_terminates_children_before_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    def fake_run(argv: list[str], **_kwargs: object) -> agents.CommandResult:
        assert argv == ["pgrep", "-P", "100"]
        return ok(tuple(argv), "200\n201\n")

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




def test_external_auth_verdict_claude_degraded_auth(tmp_path: Path) -> None:
    sidecar = tmp_path / "claude.diag"
    _ = sidecar.write_text(
        "apiKeyHelper failed: did not return a value\n"
        "claude.ai connectors are disabled because ANTHROPIC_API_KEY or another "
        "auth source takes precedence over your claude.ai login\n",
        encoding="utf-8",
    )
    assert agents.external_auth_verdict("claude", sidecar) == "auth"
    failure = agents.classify_launch_failure(
        launcher_exit=config.EXIT_TIMEOUT,
        sidecar=sidecar,
        auth_verdict="auth",
        tool="claude",
    )
    assert failure == agents.LaunchFailure("health", "auth")


def test_claude_degraded_auth_re_excludes_benign_connectors_message() -> None:
    # Regression for #5711: the benign "connectors disabled" message that appears
    # on successful runs when ANTHROPIC_API_KEY is set must not match the fast-fail
    # regex.
    benign = (
        "claude.ai connectors are disabled because ANTHROPIC_API_KEY or another "
        "auth source takes precedence over your claude.ai login"
    )
    assert agents._CLAUDE_DEGRADED_AUTH_RE.search(benign) is None  # type: ignore[attr-defined]
    assert agents._CLAUDE_DEGRADED_AUTH_RE.search("apiKeyHelper failed: did not return a value") is not None  # type: ignore[attr-defined]
    assert agents._CLAUDE_DEGRADED_AUTH_RE.search("did not return a value") is not None  # type: ignore[attr-defined]


def test_external_auth_verdict_claude_benign_connectors_only(tmp_path: Path) -> None:
    # Regression for #5711: sidecar containing only the benign connectors-disabled
    # message must not be classified as an auth failure.
    sidecar = tmp_path / "claude.diag"
    _ = sidecar.write_text(
        "claude.ai connectors are disabled because ANTHROPIC_API_KEY or another "
        "auth source takes precedence over your claude.ai login\n",
        encoding="utf-8",
    )
    assert agents.external_auth_verdict("claude", sidecar) == "non-auth"


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

@pytest.mark.parametrize(
    ("diagnostic", "fallback", "expected_model", "expected_signal"),
    [
        ("warning: Model metadata for gpt-5.6-sol not found. Defaulting", "gpt-5.6-luna", "gpt-5.6-sol", "model-metadata-not-found"),
        ("The 'gpt-5.6-terra' model requires a newer version of Codex.", "gpt-5.6-luna", "gpt-5.6-terra", "newer-codex-required"),
        ("requires a newer version of Codex", "gpt-5.6-luna", "gpt-5.6-luna", "newer-codex-required"),
        ("Model metadata for bad\x07model not found", "gpt-5.6-luna", "gpt-5.6-luna", "model-metadata-not-found"),
    ],
)
def test_detect_codex_cli_gate(
    diagnostic: str,
    fallback: str,
    expected_model: str,
    expected_signal: str,
) -> None:
    detail = agents.detect_codex_cli_gate(diagnostic, fallback_model=fallback)

    assert detail == agents.CodexGateDetail(
        model=expected_model,
        signal=expected_signal,
        message=f"codex CLI too old for {expected_model}; run `npm install -g @openai/codex@latest`",
    )


@pytest.mark.parametrize(
    "diagnostic",
    [
        "Model metadata refreshed",
        "400 invalid_request_error",
        "authentication requires a newer token",
        "quota exceeded for model metadata",
    ],
)
def test_detect_codex_cli_gate_near_misses(diagnostic: str) -> None:
    assert agents.detect_codex_cli_gate(diagnostic, fallback_model="gpt-5.6-luna") is None

def test_codex_role_model_resolution_uses_default_model_after_role_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_MODEL", "strong-global")
    monkeypatch.delenv("LARCH_CODEX_REVIEW_MODEL", raising=False)
    monkeypatch.delenv("LARCH_CODEX_VOTE_MODEL", raising=False)
    monkeypatch.delenv("LARCH_CODEX_FIX_MODEL", raising=False)

    assert agents.resolve_model_args("codex", codex_role="review", default_model="custom").argv[:2] == ("-m", "custom")
    assert agents.resolve_model_args("codex", codex_role="vote", default_model="custom").argv[:2] == ("-m", "custom")
    assert agents.resolve_model_args("codex", codex_role="fix", default_model="custom").argv[:2] == ("-m", "custom")


def test_codex_default_role_preserves_default_model_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LARCH_CODEX_MODEL", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_CODEX_MODEL", raising=False)

    assert agents.resolve_model_args("codex", codex_role="default", default_model="custom-default").argv[:2] == ("-m", "custom-default")


def test_codex_role_env_rejects_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_CODEX_REVIEW_MODEL", "   ")

    with pytest.raises(ValueError, match="LARCH_CODEX_REVIEW_MODEL"):
        agents.resolve_model_args("codex", codex_role="review")


@pytest.mark.parametrize(
    ("name", "module"),
    [
        ("TierAttempt", _types),
        ("classify_launch_failure", _launch_failure),
        ("resolve_failure_diagnostic_source", _failure_diag),
        ("run_external_agent", _run_external),
        ("check_reviewers", _auth),
    ],
)
def test_agents_reexports_split_public_contract(name: str, module: object) -> None:
    assert getattr(agents, name) is getattr(module, name)


def test_parse_codex_session_id_valid_structured_event(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"type":"item.completed","text":"thread.started ignored"}\n'
        '{"type":"thread.started","thread_id":"019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"}\n'
        '{"type":"agent.message","text":"hi"}\n',
        encoding="utf-8",
    )
    assert agents.parse_codex_session_id(events) == "019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ('{"type":"agent.message","text":"no start"}\n', "missing"),
        ("not-json\n", "malformed"),
        ('{"type":"thread.started"}\n', "missing string thread_id"),
        ('{"type":"thread.started","thread_id":123}\n', "missing string thread_id"),
        ('{"type":"thread.started","thread_id":"not-a-uuid"}\n', "invalid thread_id"),
        (
            '{"type":"thread.started","thread_id":"019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"}\n'
            '{"type":"thread.started","thread_id":"019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"}\n',
            "duplicate",
        ),
        (
            '{"type":"thread.started","thread_id":"019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"}\n'
            '{"type":"thread.started","thread_id":"019fc6b3-e6c4-7892-a97a-c80b30a7f5b1"}\n',
            "conflicting",
        ),
    ],
)
def test_parse_codex_session_id_rejects_bad_events(tmp_path: Path, payload: str, match: str) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        agents.parse_codex_session_id(events)


def test_parse_cursor_create_chat_id_requires_one_structured_record(tmp_path: Path) -> None:
    events = tmp_path / "cursor-create.jsonl"
    events.write_text('{"chatId":"debate-chat_1"}\n', encoding="utf-8")
    assert agents.parse_cursor_create_chat_id(events) == "debate-chat_1"
    events.write_text('{"chatId":"debate-chat_1"}\n{"chatId":"debate-chat_2"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        agents.parse_cursor_create_chat_id(events)


def test_opt_in_session_capture_returns_typed_handle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "codex.out"
    events = tmp_path / "events.jsonl"

    def fake_popen(*_args: object, **_kwargs: object) -> object:
        class _Proc:
            pid = 1

            def wait(self, timeout: float | None = None) -> int:
                _ = timeout
                events.write_text(
                    '{"type":"thread.started","thread_id":"019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"}\n',
                    encoding="utf-8",
                )
                output.write_text("ok\n", encoding="utf-8")
                return 0

            def poll(self) -> int | None:
                return 0

            def terminate(self) -> None:
                return None

        return _Proc()

    monkeypatch.setattr(_run_external.subprocess, "Popen", fake_popen)
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=5,
        cmd=["codex", "exec"],
        stdout_path=events,
        capture_session_handle=True,
        poll_interval=0.01,
    )
    assert result.exit_code == 0
    assert result.session_handle is not None
    assert result.session_handle.vendor == "codex"
    assert result.session_handle.session_id == "019fc6b3-e6c4-7892-a97a-c80b30a7f5b0"
    assert result.failure_reason is None


def test_session_capture_failure_is_terminal_no_auth_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "codex.out"
    events = tmp_path / "events.jsonl"
    launches = {"n": 0}

    def fake_popen(*_args: object, **_kwargs: object) -> object:
        launches["n"] += 1

        class _Proc:
            pid = 1

            def wait(self, timeout: float | None = None) -> int:
                _ = timeout
                events.write_text('{"type":"agent.message","text":"no start"}\n', encoding="utf-8")
                output.write_text("ok\n", encoding="utf-8")
                return 0

            def poll(self) -> int | None:
                return 0

            def terminate(self) -> None:
                return None

        return _Proc()

    monkeypatch.setattr(_run_external.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(_run_external, "_auth_retry_limit", lambda: 5)
    monkeypatch.setattr(_run_external, "external_startup_lock_acquire", lambda tool: agents.StartupLockState(None))  # noqa: ARG005
    monkeypatch.setattr(_run_external, "external_startup_lock_release_after", lambda state: None)  # noqa: ARG005
    result = agents._run_external_agent_with_auth_retries(  # pylint: disable=protected-access
        tool="codex",
        output=output,
        timeout_seconds=5,
        cmd=["codex", "exec"],
        stdout_path=events,
        capture_session_handle=True,
    )
    assert launches["n"] == 1
    assert result.exit_code == agents._SESSION_CAPTURE_FAILED_RC
    assert result.failure_reason == "session-capture-failed"
    assert result.failure_reason in agents.TERMINAL_EXTERNAL_AGENT_FAILURE_REASONS
    assert result.session_handle is None
    diag = output.with_suffix(output.suffix + ".diag")
    assert "session-capture-failed" in diag.read_text(encoding="utf-8")


def test_ordinary_oneshot_codex_succeeds_without_start_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "codex.out"
    events = tmp_path / "events.jsonl"

    def fake_popen(*_args: object, **_kwargs: object) -> object:
        class _Proc:
            pid = 1

            def wait(self, timeout: float | None = None) -> int:
                _ = timeout
                events.write_text('{"type":"agent.message","text":"no start"}\n', encoding="utf-8")
                output.write_text("ok\n", encoding="utf-8")
                return 0

            def poll(self) -> int | None:
                return 0

            def terminate(self) -> None:
                return None

        return _Proc()

    monkeypatch.setattr(_run_external.subprocess, "Popen", fake_popen)
    result = agents.run_external_agent(
        tool="codex",
        output=str(output),
        timeout_seconds=5,
        cmd=["codex", "exec"],
        stdout_path=events,
        poll_interval=0.01,
    )
    assert result.exit_code == 0
    assert result.session_handle is None
    assert result.failure_reason is None


def test_session_types_and_parser_reexported() -> None:
    assert agents.VendorSessionHandle is _types.VendorSessionHandle
    assert agents.parse_codex_session_id is _run_external.parse_codex_session_id
    assert agents.parse_cursor_create_chat_id is _run_external.parse_cursor_create_chat_id
    assert agents._SESSION_CAPTURE_FAILED_RC == 4
    assert "session-capture-failed" in agents.TERMINAL_EXTERNAL_AGENT_FAILURE_REASONS
