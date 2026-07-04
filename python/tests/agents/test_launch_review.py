# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for the Python review launcher."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from larch.agents import agents
from larch.agents import _review_launcher

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "python" / "cli.py"
# Subprocess stub tests can cold-start slowly under suite load, so keep the
# inner stub-agent timeout generous.
STUB_AGENT_TIMEOUT = "20"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update({
        "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT": "0",
        "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
        "LARCH_TRANSIENT_RETRY_DELAY": "0",
        "LARCH_CURSOR_LAUNCH_JITTER_MS": "0",
        # Disable the shared Darwin startup lock so these subprocess tests stay
        # hermetic. The lock dir (/tmp/larch-external-startup-<user>.lock) is
        # global; a sibling subprocess test killed before its release timer
        # fires leaks it, and the next ~30s of lock-acquiring launches block
        # until the _run timeout. Mirrors test_agent_waterfall.py.
        "LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME": "Linux",
    })
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "agent", "launch-review", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=merged,
        # Generous outer cap: each call spawns a full cli.py + agents.py import whose
        # cold-start wall time spikes under serial-suite load (observed ~10s in
        # isolation), so a 10s cap raced TimeoutExpired. The inner agent run is bounded
        # separately by the --timeout arg passed by each test.
        timeout=60,
        check=False,
    )


def _codex_review_args(tmp_path: Path, out_name: str = "out.txt", **overrides: object) -> argparse.Namespace:
    out = tmp_path / out_name
    values: dict[str, object] = {
        "output": str(out),
        "timeout": "2",
        "risk": "",
        "stderr_sink": "",
        "timing_task_kind": "codex-review",
        "token_budget_cap": "",
        "agent_file": "",
        "description_text": "",
        "mode": "",
        "scope_files": "",
        "competition_notice": False,
        "competition_notice_file": "",
        "diff_file": "",
        "commit_count": "",
        "plan_file": "",
        "feature_file": "",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _stub_bin(tmp_path: Path, name: str, body: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    path = bin_dir / name
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return bin_dir


def test_parser_rejects_invalid_timeout(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", "0", "--prompt", "hi"])
    assert proc.returncode == 2
    assert not out.exists()


def test_parser_rejects_mutually_exclusive_prompts(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("prompt", encoding="utf-8")
    proc = _run(["--tool", "cursor", "--output", str(out), "--timeout", "1", "--prompt", "hi", "--prompt-file", str(prompt_file)])
    assert proc.returncode == 2
    assert not out.exists()


def test_codex_agent_file_writes_and_replays_compact_sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = argparse.Namespace(
        agent_file="agents/code-reviewer.md",
        description_text="",
        mode="review",
        scope_files="a.py",
        competition_notice=True,
        competition_notice_file="",
        diff_file="",
        commit_count="2",
        plan_file="",
        feature_file="",
    )
    output = tmp_path / "out.txt"
    prompt = "rendered specialist"
    sidecar = agents._review_write_codex_prompt_sidecar(output=output, prompt=prompt, args=args)
    text = sidecar.read_text(encoding="utf-8")
    assert "LARCH_PROMPT_SENTINEL=1" in text
    assert "KIND=specialist" in text
    assert "HASH=" in text
    def fake_render(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"stdout": prompt, "returncode": 0})()

    monkeypatch.setattr(agents.proc, "run", fake_render)
    rc, replay = agents._review_read_codex_prompt_sentinel(str(sidecar)) or (99, "")
    assert rc == 0
    assert replay == prompt


def test_codex_sentinel_hash_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sidecar = tmp_path / "out.txt.prompt"
    sidecar.write_text(
        "LARCH_PROMPT_SENTINEL=1\nKIND=specialist\nHASH=bad\nAGENT_FILE=a\nMODE=m\n",
        encoding="utf-8",
    )
    def fake_mismatch_render(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"stdout": "different", "returncode": 0})()

    monkeypatch.setattr(agents.proc, "run", fake_mismatch_render)
    rc, replay = agents._review_read_codex_prompt_sentinel(str(sidecar)) or (99, "")
    assert rc == 1
    assert replay == ""


def test_token_budget_cap_from_env_writes_done_and_skips_vendor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"

    def fake_run(argv: list[str], **_kwargs: object) -> object:
        assert argv[2:4] == ["token", "check-budget"]
        return type("R", (), {"stdout": "STATUS=cap_hit TOTAL=42\n", "returncode": 0})()

    monkeypatch.setenv("LARCH_TOKEN_BUDGET_CAP_REVIEW", "10")
    monkeypatch.setattr(agents.proc, "run", fake_run)
    args = argparse.Namespace(token_budget_cap="")
    assert agents._review_effective_token_cap(args) == 10
    assert agents._review_check_budget_or_write_cap_hit(output=output, cap=10, timing_kind="codex-review")
    assert output.read_text(encoding="utf-8") == "STATUS=cap_hit\n"
    assert output.with_suffix(output.suffix + ".done").read_text(encoding="utf-8") == "0\n"


def test_session_id_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = tmp_path / "impl"
    design = tmp_path / "design"
    impl.mkdir()
    design.mkdir()
    (impl / "session-id").write_text("impl-session\n", encoding="utf-8")
    (design / "session-id").write_text("design-session\n", encoding="utf-8")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "preexisting")
    agents._review_apply_session_token_env()
    assert os.environ["LARCH_TOKEN_SESSION_ID"] == "impl-session"


def test_codex_launch_uses_python_wrapper_and_read_only_argv(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        "#!/usr/bin/env bash\nout=\"\"; last=\"\"; for a in \"$@\"; do if [[ \"$last\" == \"--output-last-message\" ]]; then out=\"$a\"; fi; last=\"$a\"; done; echo '{\"type\":\"message\",\"usage\":{\"input_tokens\":1,\"cached_input_tokens\":0,\"output_tokens\":2}}'; printf OK >\"$out\"\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi", "--model-role", "review"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "LARCH_CODEX_REVIEW_MODEL": "cheap-review"},
    )
    assert proc.returncode == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert "CMD_JSON=[" in meta
    assert '"codex","exec","--sandbox","read-only"' in meta
    assert '"-m","cheap-review"' in meta
    assert "OUTER_LAUNCHER=agent launch-review" in meta
    assert "OUTER_LAUNCHER_MODEL_ROLE=review" in meta
    assert out.with_suffix(out.suffix + ".inner.done").exists() is False
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8") == "0\n"
    assert "REASON=codex-sandbox-read-only" in out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")


def test_cursor_launch_extracts_result_and_writes_original_prompt_sidecar(tmp_path: Path) -> None:
    # Generic (non-plan-review) cursor-review keeps a preamble+sentinel clean even with
    # inflated inputTokens; plan-review no-issues with inlined plan is covered in test_agents.py.
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        "#!/usr/bin/env bash\ncat <<'JSON'\n{\"result\":\"Reviewing... {\\\"no_issues_found\\\": true}\",\"usage\":{\"inputTokens\":5000,\"outputTokens\":2,\"cacheReadTokens\":0,\"cacheWriteTokens\":0}}\nJSON\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(["--tool", "cursor", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"})
    assert proc.returncode == 0
    assert out.read_text(encoding="utf-8") == '{"no_issues_found": true}\n'
    assert out.with_suffix(out.suffix + ".prompt").read_text(encoding="utf-8") == "hi"
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert '"cursor","agent","-p","--trust","--mode","ask"' in meta
    assert "--api-key" not in meta
    assert "OUTER_LAUNCHER=agent launch-review" in meta


def test_cursor_plan_review_launch_keeps_no_issues_with_inlined_plan_input(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        "#!/usr/bin/env bash\ncat <<'JSON'\n{\"result\":\"{\\\"no_issues_found\\\": true}\",\"usage\":{\"inputTokens\":5000,\"outputTokens\":8,\"cacheReadTokens\":1200,\"cacheWriteTokens\":0}}\nJSON\n",
    )
    out = tmp_path / "cursor-plan-arch-output.txt"
    proc = _run(
        [
            "--tool",
            "cursor",
            "--output",
            str(out),
            "--timeout",
            STUB_AGENT_TIMEOUT,
            "--prompt",
            "hi",
            "--timing-task-kind",
            "cursor-phase1-cursor-plan-arch",
        ],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"},
    )
    assert proc.returncode == 0
    assert out.read_text(encoding="utf-8") == '{"no_issues_found": true}\n'


def test_launch_review_without_panel_slot_writes_no_panel_prompt_sizes(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        "#!/usr/bin/env bash\ncat <<'JSON'\n{\"result\":\"ok\",\"usage\":{\"inputTokens\":1,\"outputTokens\":1,\"cacheReadTokens\":0,\"cacheWriteTokens\":0}}\nJSON\n",
    )
    out = tmp_path / "scout-dynamic-output.raw"
    proc = _run(
        [
            "--tool",
            "cursor",
            "--output",
            str(out),
            "--timeout",
            STUB_AGENT_TIMEOUT,
            "--prompt",
            "scout prompt body",
            "--timing-task-kind",
            "scout-dynamic-archetypes",
        ],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"},
    )
    assert proc.returncode == 0
    assert not list(tmp_path.rglob("panel-prompt-sizes.tsv"))


def test_codex_add_dir_rejects_missing_output_parent(tmp_path: Path) -> None:
    out = tmp_path / "missing" / "out.txt"
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"])
    assert proc.returncode == 2
    assert not out.exists()


def test_render_specialist_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_render(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"stdout": "", "stderr": "render failed", "returncode": 1})()

    monkeypatch.setattr(agents.proc, "run", fail_render)
    args = argparse.Namespace(
        agent_file="agents/missing.md",
        mode="review",
        description_text="",
        scope_files="",
        competition_notice_file="",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        competition_notice=False,
    )
    rc, prompt = agents._review_render_specialist_prompt(args)
    assert rc == 1
    assert prompt == ""


def test_render_specialist_payload_sidecar_threads_into_panel_telemetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = argparse.Namespace(
        output=str(tmp_path / "out.txt"),
        agent_file="agents/reviewer-structure.md",
        mode="description",
        description_text="payload description",
        scope_files=str(tmp_path / "scope.txt"),
        competition_notice=False,
        competition_notice_file="",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
        findings_ledger_file="",
        session_env_path="",
        site="review Step 2",
        tool="cursor",
    )
    (tmp_path / "scope.txt").write_text("python/foo.py\n", encoding="utf-8")

    def fake_render(argv: list[str], **_kwargs: object) -> object:
        sidecar_idx = argv.index("--payload-bytes-output") + 1
        Path(argv[sidecar_idx]).write_text("19\n", encoding="utf-8")
        return type("R", (), {"stdout": "rendered prompt body\n", "stderr": "", "returncode": 0})()

    captured: list[dict[str, object]] = []
    monkeypatch.setattr(_review_launcher.proc, "run", fake_render)
    monkeypatch.setattr(_review_launcher, "_panel_logging_enabled", lambda: True)
    monkeypatch.setattr(_review_launcher, "append_panel_prompt_size", lambda **kwargs: captured.append(kwargs))

    rc, prompt, payload_bytes = _review_launcher._review_render_specialist_prompt_with_payload(args)  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert prompt == "rendered prompt body\n"
    assert payload_bytes == 19

    _review_launcher._review_log_panel_prompt_size(args=args, output=Path(args.output), prompt=prompt, payload_bytes=payload_bytes)  # pyright: ignore[reportPrivateUsage]
    assert captured[0]["payload_bytes"] == 19
    assert captured[0]["site"] == "review Step 2"
    assert captured[0]["output"] == Path(args.output)


def test_cursor_launch_writes_sidecar_ok_status(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        "#!/usr/bin/env bash\ncat <<'JSON'\n{\"result\":\"ok\",\"usage\":{\"inputTokens\":1,\"outputTokens\":2,\"cacheReadTokens\":0,\"cacheWriteTokens\":0}}\nJSON\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(["--tool", "cursor", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"})
    assert proc.returncode == 0
    sidecar = out.with_suffix(out.suffix + ".sidecar")
    assert sidecar.is_file()
    assert "cursor-status: ok (no stderr emitted during agent run)" in sidecar.read_text(encoding="utf-8")


def test_cursor_postprocess_writes_atomically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    payload = '{"result":"atomic-result","usage":{"inputTokens":1,"outputTokens":2}}'
    output.write_text(payload, encoding="utf-8")
    writes: list[tuple[Path, str]] = []
    real_write = agents._write

    def track_write(path: Path, text: str) -> None:
        if str(path).endswith(".atomic.tmp"):
            writes.append((path, text))
        real_write(path=path, text=text)

    monkeypatch.setattr(_review_launcher, "_write", track_write)
    agents._review_cursor_postprocess(output=output, transient_attempt=1)
    assert output.read_text(encoding="utf-8") == "atomic-result"
    assert any(text == "atomic-result" for _path, text in writes)


def test_cursor_empty_result_diag_is_redacted(tmp_path: Path) -> None:
    secret_path = f"/Users/testuser/larch3/session-{os.getpid()}"
    payload = json.dumps({"result": "", "usage": {"inputTokens": 1, "outputTokens": 0}, "request_id": secret_path})
    output = tmp_path / "out.txt"
    output.write_text(payload, encoding="utf-8")
    agents._review_cursor_postprocess(output=output, transient_attempt=1)
    diag = output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")
    assert secret_path not in diag
    assert "<OPERATOR_REPO_PATH>" in diag


def test_codex_auth_setup_preflight_exits_zero_with_clean_dirty_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _codex_review_args(tmp_path)
    out = Path(args.output)
    def auth_setup_failed(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (1, "codex auth setup failed")

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", auth_setup_failed)
    rc = agents._review_launch_codex(args=args, prompt="hi")
    assert rc == 0
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=clean" in dirty
    assert "REASON=codex-sandbox-read-only" in dirty
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8").strip() == "1"


def test_preflight_meta_writes_stderr_sink_for_collector_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sink = tmp_path / "stderr.log"
    args = _codex_review_args(tmp_path, stderr_sink=str(sink))
    out = Path(args.output)
    def auth_setup_failed(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (1, "codex auth setup failed")

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", auth_setup_failed)
    assert agents._review_launch_codex(args=args, prompt="hi") == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert f"STDERR_SINK={sink}" in meta
    assert "OUTER_LAUNCHER_STDERR_SINK" not in meta


def _codex_preflight_auth_setup_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    def prepare_failed(*_args: object, **_kwargs: object) -> tuple[int, str]:
        return (1, "preflight setup failed")

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", prepare_failed)


def _cursor_preflight_auth_setup_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    def auth_failed(**_kwargs: object) -> agents.AuthVerdict:
        return agents.AuthVerdict(ok=False, rc=1, message="preflight failed")

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", auth_failed)


@pytest.mark.parametrize(
    ("tool", "setup", "expected_rc"),
    [
        ("codex", _codex_preflight_auth_setup_failed, 0),
        ("cursor", _cursor_preflight_auth_setup_failed, 1),
    ],
)
def test_review_preflight_failure_auth_from_retry_diag_with_stderr_sink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tool: str,
    setup: Callable[[pytest.MonkeyPatch], None],
    expected_rc: int,
) -> None:
    out = tmp_path / "review.txt"
    sink = tmp_path / "launcher.log"
    retry_diag = tmp_path / "review-retry.txt.failure-diag"
    auth_text = "not logged in\n" if tool == "codex" else "authentication failed\n"
    _ = retry_diag.write_text(auth_text, encoding="utf-8")
    _ = sink.write_text("benign launcher noise\n", encoding="utf-8")
    setup(monkeypatch)
    if tool == "codex":
        args = _codex_review_args(tmp_path, out_name="review.txt", stderr_sink=str(sink))
        assert agents._review_launch_codex(args=args, prompt="hi") == expected_rc
    else:
        args = argparse.Namespace(
            output=str(out),
            timeout="2",
            risk="",
            stderr_sink=str(sink),
            timing_task_kind="cursor-review",
            token_budget_cap="",
        )
        assert agents._review_launch_cursor(args=args, original_prompt="hi") == expected_rc
    stdout = capsys.readouterr().out
    assert "LAUNCHER_FAILURE_CLASS=health" in stdout
    assert "LAUNCHER_FAILURE_REASON=auth" in stdout
    failure_diag = out.with_suffix(out.suffix + ".failure-diag")
    assert failure_diag.is_file()
    assert "benign launcher noise" in failure_diag.read_text(encoding="utf-8")


def test_codex_sentinel_replays_with_ns_retry_header_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ns_header = agents._COLLECTOR_NS_STRONG_HEADER
    args = argparse.Namespace(
        agent_file="agents/code-reviewer.md",
        description_text="",
        mode="review",
        scope_files="a.py",
        competition_notice=True,
        competition_notice_file="",
        diff_file="",
        commit_count="2",
        plan_file="",
        feature_file="",
    )
    output = tmp_path / "out.txt"
    prompt = "rendered specialist"
    sidecar = agents._review_write_codex_prompt_sidecar(output=output, prompt=prompt, args=args)
    wrapped = tmp_path / "ns-retry.prompt"
    wrapped.write_text(ns_header + sidecar.read_text(encoding="utf-8"), encoding="utf-8")

    def fake_render(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"stdout": prompt, "returncode": 0})()

    monkeypatch.setattr(agents.proc, "run", fake_render)
    rc, replay = agents._review_read_codex_prompt_sentinel(str(wrapped)) or (99, "")
    assert rc == 0
    assert replay == ns_header + prompt


def test_codex_retry_auth_only_from_stderr_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    events = output.with_suffix(output.suffix + ".events.jsonl")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    calls = {"count": 0}
    monkeypatch.setenv("LARCH_EXTERNAL_AUTH_RETRIES", "2")

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        events.write_text('{"type":"message","text":"Error: not logged in"}\n', encoding="utf-8")
        sidecar.write_text("", encoding="utf-8")
        output.write_text("failed\n", encoding="utf-8")
        return agents.RunExternalAgentResult(7, output)

    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    result, auth_attempt, _transient_attempt = agents._review_run_with_retries(
        tool="codex",
        output=output,
        timeout_seconds=2,
        cmd=["codex", "exec"],
        stdout_path=events,
        stderr_path=sidecar,
    )
    assert calls["count"] == 1
    assert auth_attempt == 1
    assert result.exit_code == 7


def test_codex_retry_auth_from_stderr_sidecar_retries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    events = output.with_suffix(output.suffix + ".events.jsonl")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    calls = {"count": 0}
    monkeypatch.setenv("LARCH_EXTERNAL_AUTH_RETRIES", "2")

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        events.write_text("{}\n", encoding="utf-8")
        sidecar.write_text("Error: not logged in\n", encoding="utf-8")
        output.write_text("failed\n", encoding="utf-8")
        return agents.RunExternalAgentResult(7, output)

    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    _result, auth_attempt, _transient_attempt = agents._review_run_with_retries(
        tool="codex",
        output=output,
        timeout_seconds=2,
        cmd=["codex", "exec"],
        stdout_path=events,
        stderr_path=sidecar,
    )
    assert calls["count"] == 2
    assert auth_attempt == 2


def test_codex_retry_unclassified_empty_exit_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    events = output.with_suffix(output.suffix + ".events.jsonl")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    calls = {"count": 0}
    monkeypatch.setenv("LARCH_EXTERNAL_AUTH_RETRIES", "5")

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        events.write_text("", encoding="utf-8")
        sidecar.write_text("", encoding="utf-8")
        output.write_text("", encoding="utf-8")
        exit_code = 1 if calls["count"] == 1 else 3
        return agents.RunExternalAgentResult(exit_code, output)

    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    result, auth_attempt, _transient_attempt = agents._review_run_with_retries(
        tool="codex",
        output=output,
        timeout_seconds=2,
        cmd=["codex", "exec"],
        stdout_path=events,
        stderr_path=sidecar,
    )
    assert calls["count"] == 2
    assert result.exit_code == 3
    assert auth_attempt == 1


def test_codex_retry_unclassified_empty_exit_one_respects_auth_retry_limit_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "out.txt"
    events = output.with_suffix(output.suffix + ".events.jsonl")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    calls = {"count": 0}
    monkeypatch.setenv("LARCH_EXTERNAL_AUTH_RETRIES", "1")

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        events.write_text("", encoding="utf-8")
        sidecar.write_text("", encoding="utf-8")
        output.write_text("", encoding="utf-8")
        return agents.RunExternalAgentResult(1, output)

    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    result, auth_attempt, _transient_attempt = agents._review_run_with_retries(
        tool="codex",
        output=output,
        timeout_seconds=2,
        cmd=["codex", "exec"],
        stdout_path=events,
        stderr_path=sidecar,
    )
    assert calls["count"] == 2
    assert result.exit_code == 1
    assert auth_attempt == 1


def test_review_startup_lock_releases_before_blocking_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    order: list[str] = []

    def fake_acquire(**_kwargs: object) -> agents.StartupLockState:  # type: ignore[return-value]
        order.append("acquire")
        return agents.StartupLockState(None)

    def fake_release(**_kwargs: object) -> None:
        order.append("release")

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        order.append("run")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_review_launcher, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(_review_launcher, "external_startup_lock_release_after", fake_release)
    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    agents._review_run_wrapper_attempt(tool="cursor", output=output, timeout_seconds=1, cmd=["cursor"])
    assert order == ["acquire", "release", "run"]


def test_cursor_review_records_usage_via_sidecar_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    json_sidecar = tmp_path / "json.out"
    payload = '{"result":"ok","usage":{"inputTokens":3,"outputTokens":7,"cacheReadTokens":0,"cacheWriteTokens":0}}'
    json_sidecar.write_text(payload, encoding="utf-8")
    calls: list[tuple[str, str]] = []

    def track_run(argv: list[str], **_kwargs: object) -> object:
        calls.append((argv[2], argv[3]))
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(agents.proc, "run", track_run)
    agents._review_cursor_postprocess(output=json_sidecar, transient_attempt=1)
    assert calls == [("token", "record-vendor-sidecar")]


def test_codex_review_ingests_token_record_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []
    real_run = agents.proc.run

    def track_run(argv: list[str], **_kwargs: Any) -> object:
        if len(argv) >= 4 and argv[2] == "token":
            calls.append((argv[2], argv[3]))
        return real_run(argv, **_kwargs)

    monkeypatch.setattr(agents.proc, "run", track_run)
    args = _codex_review_args(tmp_path)
    out = Path(args.output)
    events = out.with_suffix(out.suffix + ".events.jsonl")
    events.write_text(
        '{"type":"message","usage":{"input_tokens":4,"cached_input_tokens":1,"output_tokens":2}}\n',
        encoding="utf-8",
    )
    def auth_setup_ok(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (0, "")

    def run_with_retries_ok(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", auth_setup_ok)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_ok)
    assert agents._review_launch_codex(args=args, prompt="hi") == 0
    assert out.with_suffix(out.suffix + ".token-record").is_file()
    assert ("token", "record-vendor-sidecar") in calls
    assert ("token", "record-vendor") not in calls


def test_codex_terminal_artifacts_order_metadata_usage_dirty_tree_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _codex_review_args(tmp_path)
    out = Path(args.output)
    order: list[str] = []

    def auth_setup_ok(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (0, "")

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def run_with_retries_ok(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    def append_outer_meta(*_args: object, **_kwargs: object) -> None:
        order.append("metadata")

    def record_usage(*_args: object, **_kwargs: object) -> None:
        order.append("usage")

    def write_clean_dirty_tree(_output: Path) -> None:
        order.append("dirty-tree")

    def promote_inner_done(_output: Path) -> None:
        order.append("done")

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", auth_setup_ok)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_ok)
    monkeypatch.setattr(_review_launcher, "_review_append_outer_meta", append_outer_meta)
    monkeypatch.setattr(_review_launcher, "_record_usage_from_events", record_usage)
    monkeypatch.setattr(_review_launcher, "_review_write_clean_readonly_dirty_tree", write_clean_dirty_tree)
    monkeypatch.setattr(_review_launcher, "_promote_inner_done", promote_inner_done)

    assert agents._review_launch_codex(args=args, prompt="hi") == 0
    assert order == ["metadata", "usage", "dirty-tree", "done"]


def test_codex_transient_retry_succeeds_on_second_attempt(tmp_path: Path) -> None:
    state = tmp_path / "attempts"
    state.write_text("0", encoding="utf-8")
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        f"""#!/usr/bin/env bash
state="{state}"
n=$(cat "$state"); echo $((n+1)) > "$state"
out=""; last=""; for a in "$@"; do if [[ "$last" == "--output-last-message" ]]; then out="$a"; fi; last="$a"; done
if [[ "$n" == "0" ]]; then exit 7; fi
echo '{{"type":"message","usage":{{"input_tokens":1,"cached_input_tokens":0,"output_tokens":2}}}}'
printf OK >"$out"
""",
    )
    out = tmp_path / "out.txt"
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}"})
    assert proc.returncode == 0
    assert state.read_text(encoding="utf-8").strip() == "2"
    assert out.read_text(encoding="utf-8") == "OK"


def test_cursor_auth_preflight_writes_preflight_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    def cursor_auth_missing(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=False, rc=1, message="cursor auth missing")

    monkeypatch.setattr(
        _review_launcher,
        "cursor_auth_preflight",
        cursor_auth_missing,
    )
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 1
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8").strip() == "1"
    diag = out.with_suffix(out.suffix + ".diag").read_text(encoding="utf-8")
    assert "STATUS=FAILED" in diag
    assert "cursor-auth-preflight" in diag
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=unknown" in dirty
    assert "preflight-short-circuit-no-agent-ran" in dirty


def test_cursor_degraded_response_written_when_validation_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        '#!/usr/bin/env bash\ncat <<\'JSON\'\n{"result":"short","usage":{"inputTokens":1,"outputTokens":1001,"cacheReadTokens":0,"cacheWriteTokens":0}}\nJSON\n',
    )
    out = tmp_path / "out.txt"
    real_run = agents.proc.run

    def selective_run(argv: list[str], **_kwargs: Any) -> object:
        if len(argv) >= 5 and argv[2:5] == ["eval", "validate-research-output"]:
            return type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})()
        return real_run(argv, **_kwargs)

    monkeypatch.setattr(agents.proc, "run", selective_run)
    proc = _run(
        ["--tool", "cursor", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"},
    )
    assert proc.returncode == 0
    assert out.read_text(encoding="utf-8") == "CURSOR_DEGRADED_RESPONSE\n"


def test_cursor_done_promoted_after_timing_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    real_timing = agents._review_record_timing
    real_promote = agents._promote_inner_done
    out = tmp_path / "out.txt"

    def track_timing(*args: object, **_kwargs: object) -> None:
        order.append("timing")
        real_timing(*args, **_kwargs)  # type: ignore[arg-type]

    def track_promote(output: Path) -> None:
        order.append("done")
        real_promote(output)

    monkeypatch.setattr(_review_launcher, "_review_record_timing", track_timing)
    monkeypatch.setattr(_review_launcher, "_promote_inner_done", track_promote)
    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(cfg_tmp: Path, old_cfg: str | None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def write_cursor_dirty_tree_from_baseline(**_kwargs: object) -> None:
        return None

    def cursor_postprocess(**_kwargs: object) -> None:
        return None

    def run_with_retries_ok(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(_review_launcher, "_review_write_cursor_dirty_tree_from_baseline", write_cursor_dirty_tree_from_baseline)
    monkeypatch.setattr(_review_launcher, "_review_cursor_postprocess", cursor_postprocess)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_ok)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 0
    assert order == ["timing", "done"]


def test_cursor_terminal_artifacts_order_metadata_trap_postprocess_dirty_tree_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    order: list[str] = []

    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(cfg_tmp: Path, old_cfg: str | None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def run_with_retries_ok(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    def append_outer_meta(*_args: object, **_kwargs: object) -> None:
        order.append("metadata")

    def run_trap() -> None:
        order.append("trap")

    def cursor_postprocess(**_kwargs: object) -> None:
        order.append("postprocess")

    def write_cursor_dirty_tree_from_baseline(**_kwargs: object) -> None:
        order.append("dirty-tree")

    def promote_inner_done(_output: Path) -> None:
        order.append("done")

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_ok)
    monkeypatch.setattr(_review_launcher, "_review_append_outer_meta", append_outer_meta)
    monkeypatch.setattr(_review_launcher, "_review_run_test_trap_after_inner_done_if_enabled", run_trap)
    monkeypatch.setattr(_review_launcher, "_review_cursor_postprocess", cursor_postprocess)
    monkeypatch.setattr(_review_launcher, "_review_write_cursor_dirty_tree_from_baseline", write_cursor_dirty_tree_from_baseline)
    monkeypatch.setattr(_review_launcher, "_promote_inner_done", promote_inner_done)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )

    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 0
    assert order == ["metadata", "trap", "postprocess", "dirty-tree", "done"]


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True, text=True)
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


def _codex_launch_cmd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    args = _codex_review_args(tmp_path)
    out = Path(args.output)
    captured: dict[str, list[str]] = {}

    def auth_setup_ok(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (0, "")

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def run_with_retries_ok(**kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        cmd = kwargs["cmd"]
        if not isinstance(cmd, list):
            raise TypeError("cmd must be a list")
        cmd_values = cast("list[object]", cmd)
        captured["cmd"] = [str(value) for value in cmd_values]
        out.write_text("ok\n", encoding="utf-8")
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    def record_usage_noop(*_args: object, **_kwargs: object) -> None:
        return None

    def record_timing_noop(*_args: object, **_kwargs: object) -> None:
        return None

    def write_dirty_tree_noop(_output: Path) -> None:
        return None

    def promote_done_noop(_output: Path) -> None:
        return None

    def emit_launcher_result_noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", auth_setup_ok)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_ok)
    monkeypatch.setattr(_review_launcher, "_record_usage_from_events", record_usage_noop)
    monkeypatch.setattr(_review_launcher, "_review_record_timing", record_timing_noop)
    monkeypatch.setattr(_review_launcher, "_review_write_clean_readonly_dirty_tree", write_dirty_tree_noop)
    monkeypatch.setattr(_review_launcher, "_promote_inner_done", promote_done_noop)
    monkeypatch.setattr(_review_launcher, "_review_emit_launcher_result", emit_launcher_result_noop)

    assert agents._review_launch_codex(args=args, prompt="hi") == 0
    return captured["cmd"]


def _codex_workdir_from_cmd(cmd: list[str]) -> Path:
    return Path(cmd[cmd.index("-C") + 1])


def _codex_trust_config_from_cmd(cmd: list[str]) -> str:
    for value in cmd:
        if value.startswith("projects."):
            return value
    raise AssertionError("missing codex trust config")


def test_codex_launch_resolves_workdir_to_git_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    _init_git_repo(repo)
    nested = repo / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    cmd = _codex_launch_cmd(tmp_path, monkeypatch)

    assert _codex_workdir_from_cmd(cmd).resolve() == repo.resolve()
    assert str(repo.resolve()) in _codex_trust_config_from_cmd(cmd)


def test_codex_launch_resolves_workdir_from_plugin_cache_via_keepalive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _init_git_repo(consumer)
    plugin_cache = tmp_path / "plugin-cache"
    plugin_cache.mkdir()
    design_tmp = tmp_path / "design"
    design_tmp.mkdir()
    (design_tmp / ".larch-keepalive").write_text(f"CLONE_PATH={consumer}\n", encoding="utf-8")
    monkeypatch.chdir(plugin_cache)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_tmp))
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.delenv("SESSION_TMPDIR", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    cmd = _codex_launch_cmd(tmp_path, monkeypatch)

    assert _codex_workdir_from_cmd(cmd).resolve() == consumer.resolve()
    assert str(consumer.resolve()) in _codex_trust_config_from_cmd(cmd)


def test_resolve_workdir_reads_implement_tmpdir_keepalive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _init_git_repo(consumer)
    plugin_cache = tmp_path / "plugin-cache"
    plugin_cache.mkdir()
    implement_tmp = tmp_path / "implement"
    implement_tmp.mkdir()
    (implement_tmp / ".larch-keepalive").write_text(f"CLONE_PATH={consumer}\n", encoding="utf-8")
    monkeypatch.chdir(plugin_cache)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(implement_tmp))
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    monkeypatch.delenv("SESSION_TMPDIR", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    resolved = agents._resolve_review_codex_workdir(str(plugin_cache))

    assert Path(resolved).resolve() == consumer.resolve()


def test_codex_launch_resolves_workdir_from_claude_project_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _init_git_repo(consumer)
    plugin_cache = tmp_path / "plugin-cache"
    plugin_cache.mkdir()
    monkeypatch.chdir(plugin_cache)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(consumer))

    cmd = _codex_launch_cmd(tmp_path, monkeypatch)

    assert _codex_workdir_from_cmd(cmd).resolve() == consumer.resolve()
    assert str(consumer.resolve()) in _codex_trust_config_from_cmd(cmd)


def _cursor_review_launch_cmd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    out = tmp_path / "review-out.txt"
    captured: dict[str, list[str]] = {}

    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(cfg_tmp: Path, old_cfg: str | None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def run_with_retries_capture(**kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        cmd = kwargs["cmd"]
        if not isinstance(cmd, list):
            raise TypeError("cmd must be a list")
        cmd_values = cast("list[object]", cmd)
        captured["cmd"] = [str(value) for value in cmd_values]
        out.write_text("ok\n", encoding="utf-8")
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    def noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_capture)
    monkeypatch.setattr(_review_launcher, "_review_append_outer_meta", noop)
    monkeypatch.setattr(_review_launcher, "_review_run_test_trap_after_inner_done_if_enabled", lambda: None)
    monkeypatch.setattr(_review_launcher, "_review_cursor_postprocess", noop)
    monkeypatch.setattr(_review_launcher, "_review_write_cursor_dirty_tree_from_baseline", noop)
    monkeypatch.setattr(_review_launcher, "_promote_inner_done", noop)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )

    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 0
    return captured["cmd"]


def _cursor_workspace_from_cmd(cmd: list[str]) -> Path:
    return Path(cmd[cmd.index("--workspace") + 1])


def test_cursor_review_resolves_workspace_to_git_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    _init_git_repo(repo)
    nested = repo / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    cmd = _cursor_review_launch_cmd(tmp_path, monkeypatch)

    assert _cursor_workspace_from_cmd(cmd).resolve() == repo.resolve()


def test_codex_model_args_preflight_exit_one_with_unknown_dirty_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _codex_review_args(tmp_path)

    def prepare_ok(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (0, "")

    def model_args_fail(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        raise ValueError("bad codex model")

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", prepare_ok)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", model_args_fail)
    out = Path(args.output)
    assert agents._review_launch_codex(args=args, prompt="hi") == 1
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=unknown" in dirty
    assert "model-args-preflight-no-agent-ran" in dirty
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8").strip() == "1"
    assert "model-args failed" in out.with_suffix(out.suffix + ".diag").read_text(encoding="utf-8")


def test_cursor_model_args_preflight_exit_one_with_unknown_dirty_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"

    def model_args_fail(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        raise ValueError("bad cursor model")

    monkeypatch.setattr(_review_launcher, "resolve_model_args", model_args_fail)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 1
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=unknown" in dirty
    assert "model-args-preflight-no-agent-ran" in dirty
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8").strip() == "1"
    assert "load_model_args failed" in out.with_suffix(out.suffix + ".diag").read_text(encoding="utf-8")
    assert out.with_suffix(out.suffix + ".prompt").read_text(encoding="utf-8") == "hi"
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert "OUTER_LAUNCHER=agent launch-review" in meta
    assert f"OUTER_LAUNCHER_PROMPT_FILE={out}.prompt" in meta
    assert "OUTER_LAUNCHER_WORKDIR=" in meta


def test_invalid_token_budget_cap_zero_still_runs_vendor(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        '#!/usr/bin/env bash\ncat <<\'JSON\'\n{"result":"ok","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\nJSON\n',
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "cursor", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key", "LARCH_TOKEN_BUDGET_CAP_REVIEW": "0"},
    )
    assert proc.returncode == 0
    assert out.read_text(encoding="utf-8") == "ok"


def test_invalid_token_budget_cap_abc_still_runs_vendor(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        '#!/usr/bin/env bash\ncat <<\'JSON\'\n{"result":"ok","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\nJSON\n',
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "cursor", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key", "LARCH_TOKEN_BUDGET_CAP_REVIEW": "abc"},
    )
    assert proc.returncode == 0
    assert out.read_text(encoding="utf-8") == "ok"


def test_cursor_preexisting_untracked_baseline_stays_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "preexisting.txt").write_text("baseline\n", encoding="utf-8")
    out = tmp_path / "out.txt"

    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(cfg_tmp: Path, old_cfg: str | None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        return None

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        out.write_text('{"result":"ok","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, out)

    monkeypatch.chdir(repo)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 0
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=clean" in dirty
    assert out.with_suffix(out.suffix + ".untracked-baseline").is_file()


def test_cursor_reviewer_untracked_yields_dirty_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "preexisting.txt").write_text("baseline\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    monkeypatch.chdir(repo)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    baseline = agents._review_capture_cursor_dirty_baseline(out)
    (repo / "reviewer-new.txt").write_text("reviewer\n", encoding="utf-8")
    agents._review_write_cursor_dirty_tree_from_baseline(output=out, baseline=baseline)
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=dirty" in dirty
    new_untracked = out.with_suffix(out.suffix + ".dirty-tree.new-untracked-paths")
    assert new_untracked.is_file()
    assert b"reviewer-new.txt" in new_untracked.read_bytes()


def test_cursor_dirty_tree_resolves_consumer_repo_from_non_git_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression for #4452: when the review subprocess CWD is the plugin cache dir
    # (not a git repo), the cursor dirty-tree path must resolve the consumer repo via
    # CLAUDE_PROJECT_DIR instead of reporting STATUS=unknown / git-status-failed.
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _init_git_repo(consumer)
    plugin_cache = tmp_path / "plugin-cache"
    plugin_cache.mkdir()
    out = tmp_path / "out.txt"
    monkeypatch.chdir(plugin_cache)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(consumer))
    baseline = agents._review_capture_cursor_dirty_baseline(out)
    agents._review_write_cursor_dirty_tree_from_baseline(output=out, baseline=baseline)
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=clean" in dirty
    assert "git-status-failed" not in dirty


def test_cursor_empty_result_retries_with_lock_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    calls = {"count": 0, "locks": 0}

    def fake_acquire(**_kwargs: object) -> agents.StartupLockState:  # type: ignore[return-value]
        calls["locks"] += 1
        return agents.StartupLockState(None)

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        if calls["count"] == 1:
            output.write_text('{"result":"","usage":{"inputTokens":1,"outputTokens":0}}\n', encoding="utf-8")
        else:
            output.write_text('{"result":"ok","usage":{"inputTokens":1,"outputTokens":2}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    def fake_release(**_kwargs: object) -> None:
        return None

    monkeypatch.setenv("LARCH_CURSOR_RETRY_EMPTY_RESULT", "1")
    monkeypatch.setattr(_review_launcher, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(_review_launcher, "external_startup_lock_release_after", fake_release)
    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    _result, _auth_attempt, transient_attempt = agents._review_run_with_retries(
        tool="cursor",
        output=output,
        timeout_seconds=2,
        cmd=["cursor", "agent"],
        capture_stdout_only=True,
    )
    assert calls["count"] == 2
    assert calls["locks"] == 2
    assert transient_attempt == 2


def test_cursor_empty_result_skips_retry_when_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    calls = {"count": 0, "locks": 0}

    def fake_acquire(**_kwargs: object) -> agents.StartupLockState:  # type: ignore[return-value]
        calls["locks"] += 1
        return agents.StartupLockState(None)

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        output.write_text('{"result":"","usage":{"inputTokens":1,"outputTokens":0}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    def fake_release(**_kwargs: object) -> None:
        return None

    monkeypatch.setenv("LARCH_CURSOR_RETRY_EMPTY_RESULT", "0")
    monkeypatch.setattr(_review_launcher, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(_review_launcher, "external_startup_lock_release_after", fake_release)
    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    _result, _auth_attempt, transient_attempt = agents._review_run_with_retries(
        tool="cursor",
        output=output,
        timeout_seconds=2,
        cmd=["cursor", "agent"],
        capture_stdout_only=True,
    )
    assert calls["count"] == 1
    assert calls["locks"] == 1
    assert transient_attempt == 1


def test_codex_quota_failure_skips_transient_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    events = output.with_suffix(output.suffix + ".events.jsonl")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    calls = {"count": 0}

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        events.write_text('{"type":"error","message":"usage limit exceeded"}\n', encoding="utf-8")
        sidecar.write_text("codex-quota: usage limit / quota reported\n", encoding="utf-8")
        output.write_text("failed\n", encoding="utf-8")
        return agents.RunExternalAgentResult(7, output)

    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    _result, _auth_attempt, transient_attempt = agents._review_run_with_retries(
        tool="codex",
        output=output,
        timeout_seconds=2,
        cmd=["codex", "exec"],
        stdout_path=events,
        stderr_path=sidecar,
    )
    assert calls["count"] == 1
    assert transient_attempt == 1


def test_cursor_empty_result_integration_retries_stub_binary(tmp_path: Path) -> None:
    state = tmp_path / "attempts"
    state.write_text("0", encoding="utf-8")
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        f"""#!/usr/bin/env bash
state="{state}"
n=$(cat "$state"); echo $((n+1)) > "$state"
if [[ "$n" == "0" ]]; then
  cat <<'JSON'
{{"result":"","usage":{{"inputTokens":1,"outputTokens":0,"cacheReadTokens":0,"cacheWriteTokens":0}}}}
JSON
else
  cat <<'JSON'
{{"result":"ok","usage":{{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}}}
JSON
fi
""",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "cursor", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key", "LARCH_CURSOR_RETRY_EMPTY_RESULT": "1"},
    )
    assert proc.returncode == 0
    assert state.read_text(encoding="utf-8").strip() == "2"
    assert out.read_text(encoding="utf-8") == "ok"


def test_cursor_postprocess_tolerates_invalid_output_tokens(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    payload = '{"result":"ok","usage":{"inputTokens":1,"outputTokens":"not-a-number"}}'
    output.write_text(payload, encoding="utf-8")
    agents._review_cursor_postprocess(output=output, transient_attempt=1)
    assert output.read_text(encoding="utf-8") == "ok"


def test_codex_prompt_with_embedded_sentinel_reads_verbatim(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.txt"
    body = "Feature text mentions LARCH_PROMPT_SENTINEL=1 in documentation.\n"
    prompt_file.write_text(body, encoding="utf-8")
    assert agents._review_read_codex_prompt_sentinel(str(prompt_file)) is None
    rc, text = agents._review_read_prompt_file(str(prompt_file))
    assert rc == 0
    assert text == body


def test_transient_retry_clears_stale_diag_and_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    events = output.with_suffix(output.suffix + ".events.jsonl")
    diag = output.with_suffix(output.suffix + ".diag")
    calls = {"count": 0}

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        if calls["count"] == 1:
            events.write_text('{"type":"error","message":"network timeout"}\n', encoding="utf-8")
            diag.write_text("stale diag from failed attempt\n", encoding="utf-8")
            output.write_text("", encoding="utf-8")
            return agents.RunExternalAgentResult(7, output)
        assert not events.is_file()
        assert not diag.is_file()
        output.write_text("ok\n", encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    _result, _auth_attempt, transient_attempt = agents._review_run_with_retries(
        tool="codex",
        output=output,
        timeout_seconds=2,
        cmd=["codex", "exec"],
        stdout_path=events,
        stderr_path=output.with_suffix(output.suffix + ".sidecar"),
    )
    assert calls["count"] == 2
    assert transient_attempt == 2
    history = output.with_suffix(output.suffix + ".sidecar.history").read_text(encoding="utf-8")
    assert "stale diag from failed attempt" in history
    assert "network timeout" in history


def test_cursor_failure_skips_postprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    payload = '{"result":"partial review","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}'
    postprocess_calls: list[Path] = []
    real_postprocess = agents._review_cursor_postprocess

    def track_postprocess(output: Path, transient_attempt: int) -> None:
        postprocess_calls.append(output)
        real_postprocess(output=output, transient_attempt=transient_attempt)

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        out.write_text(payload, encoding="utf-8")
        return agents.RunExternalAgentResult(1, out)

    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(cfg_tmp: Path, old_cfg: str | None) -> None:  # noqa: ARG001  # pylint: disable=unused-argument
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def write_cursor_dirty_tree_from_baseline(**_kwargs: object) -> None:
        return None

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(_review_launcher, "_review_write_cursor_dirty_tree_from_baseline", write_cursor_dirty_tree_from_baseline)
    monkeypatch.setattr(_review_launcher, "_review_cursor_postprocess", track_postprocess)
    monkeypatch.setattr(_review_launcher, "run_external_agent", fake_run)
    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 1
    assert not postprocess_calls
    assert out.read_text(encoding="utf-8") == payload


def test_outer_meta_writes_timing_task_kind(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        "#!/usr/bin/env bash\nout=\"\"; last=\"\"; for a in \"$@\"; do if [[ \"$last\" == \"--output-last-message\" ]]; then out=\"$a\"; fi; last=\"$a\"; done; echo '{\"type\":\"message\",\"usage\":{\"input_tokens\":1,\"cached_input_tokens\":0,\"output_tokens\":2}}'; printf OK >\"$out\"\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        [
            "--tool",
            "codex",
            "--output",
            str(out),
            "--timeout",
            STUB_AGENT_TIMEOUT,
            "--prompt",
            "hi",
            "--timing-task-kind",
            "codex-review-round-2-correctness",
        ],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )
    assert proc.returncode == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert "OUTER_LAUNCHER_TIMING_KIND=codex-review-round-2-correctness" in meta


def test_review_parser_rejects_invalid_site(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    for bad in ("", "--flagish", "bad\x01site"):
        proc = _run(["--tool", "codex", "--output", str(out), "--timeout", "5", "--prompt", "hi", f"--site={bad}"])
        assert proc.returncode == 2, f"--site={bad!r} should be rejected"
        assert not out.exists()


def test_outer_meta_writes_site_for_codex_launch(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        "#!/usr/bin/env bash\nout=\"\"; last=\"\"; for a in \"$@\"; do if [[ \"$last\" == \"--output-last-message\" ]]; then out=\"$a\"; fi; last=\"$a\"; done; echo '{\"type\":\"message\",\"usage\":{\"input_tokens\":1,\"cached_input_tokens\":0,\"output_tokens\":2}}'; printf OK >\"$out\"\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        [
            "--tool",
            "codex",
            "--output",
            str(out),
            "--timeout",
            STUB_AGENT_TIMEOUT,
            "--prompt",
            "hi",
            "--site",
            "design Step 3",
        ],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )
    assert proc.returncode == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert "OUTER_LAUNCHER_SITE=design Step 3" in meta


def test_outer_meta_defaults_site_when_unspecified(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        "#!/usr/bin/env bash\nout=\"\"; last=\"\"; for a in \"$@\"; do if [[ \"$last\" == \"--output-last-message\" ]]; then out=\"$a\"; fi; last=\"$a\"; done; echo '{\"type\":\"message\",\"usage\":{\"input_tokens\":1,\"cached_input_tokens\":0,\"output_tokens\":2}}'; printf OK >\"$out\"\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )
    assert proc.returncode == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert "OUTER_LAUNCHER_SITE=review Step 2" in meta


def test_codex_home_is_outside_output_tree(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    external_tmp = tmp_path / "external-tmp"
    external_tmp.mkdir()
    home_log = tmp_path / "codex-home.txt"
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$CODEX_HOME" > "{home_log}"
out=""; last=""
for a in "$@"; do
  if [[ "$last" == "--output-last-message" ]]; then out="$a"; fi
  last="$a"
done
printf OK >"$out"
echo '{{"type":"message","usage":{{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}}}'
""",
    )
    out = session / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "TMPDIR": str(external_tmp)},
    )
    assert proc.returncode == 0
    codex_home = Path(home_log.read_text(encoding="utf-8").strip()).resolve()
    assert session.resolve() not in codex_home.parents

    fail_proc = _run(
        ["--tool", "codex", "--output", str(session / "out2.txt"), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "TMPDIR": str(session)},
    )
    assert fail_proc.returncode == 2






def test_codex_grants_output_parent_add_dir(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    marker = tmp_path / "add-dir.txt"
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        f"""#!/usr/bin/env bash
out=""; last=""; first_add=""
for a in "$@"; do
  if [[ "$last" == "--add-dir" && -z "$first_add" ]]; then first_add="$a"; fi
  if [[ "$last" == "--output-last-message" ]]; then out="$a"; fi
  last="$a"
done
printf '%s\n' "$first_add" > "{marker}"
printf OK >"$out"
echo '{{"type":"message","usage":{{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}}}'
""",
    )
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )
    assert proc.returncode == 0
    assert Path(marker.read_text(encoding="utf-8").strip()).resolve() == tmp_path.resolve()


def test_codex_launch_does_not_leak_openai_api_key(tmp_path: Path) -> None:
    secret = "sk-larch-review-sentinel"
    home_log = tmp_path / "codex-home.txt"
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$CODEX_HOME" > "{home_log}"
out=""; last=""
for a in "$@"; do
  if [[ "$last" == "--output-last-message" ]]; then out="$a"; fi
  last="$a"
done
printf OK >"$out"
echo '{{"type":"message","usage":{{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}}}'
""",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "OPENAI_API_KEY": secret},
    )
    assert proc.returncode == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert secret not in meta
    assert secret not in proc.stdout
    assert secret not in proc.stderr


def test_cursor_parallel_launches_use_distinct_config_dirs(tmp_path: Path) -> None:
    cfg_log = tmp_path / "cfg-dirs.txt"
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        f"""#!/usr/bin/env bash
printf '%s\\n' "${{CURSOR_CONFIG_DIR:-UNSET}}" >> "{cfg_log}"
cat <<'JSON'
{{"result":"ok","usage":{{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}}}
JSON
""",
    )
    env = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"}
    out1 = tmp_path / "out1.txt"
    out2 = tmp_path / "out2.txt"
    proc1 = _run(["--tool", "cursor", "--output", str(out1), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "one"], env)
    proc2 = _run(["--tool", "cursor", "--output", str(out2), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "two"], env)
    assert proc1.returncode == 0
    assert proc2.returncode == 0
    dirs = [line.strip() for line in cfg_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(dirs) == 2
    assert dirs[0] != dirs[1]
    assert dirs[0] != str(Path.home() / ".cursor")
    assert dirs[1] != str(Path.home() / ".cursor")


def test_codex_quota_failure_logs_to_design_tmpdir_only(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    count = tmp_path / "count.txt"
    count.write_text("0", encoding="utf-8")
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        f"""#!/usr/bin/env bash
n=$(cat "{count}"); echo $((n+1)) > "{count}"
printf "You've hit your usage limit.\\n" >&2
exit 1
""",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "quota"],
        {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "DESIGN_TMPDIR": str(design),
            "IMPLEMENT_TMPDIR": "",
            "LARCH_EXECUTION_ISSUES_LOG": "",
        },
    )
    assert proc.returncode == 1
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "Step review Step 2 — codex-review failed" in issues
    assert "quota" in issues


def test_codex_transient_exhaustion_logs_to_implement_tmpdir(tmp_path: Path) -> None:
    impl = tmp_path / "implement"
    impl.mkdir()
    count = tmp_path / "count.txt"
    count.write_text("0", encoding="utf-8")
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        f"""#!/usr/bin/env bash
n=$(cat "{count}"); echo $((n+1)) > "{count}"
exit 7
""",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "transient"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "IMPLEMENT_TMPDIR": str(impl)},
    )
    assert proc.returncode == 7
    issues = (impl / "execution-issues.md").read_text(encoding="utf-8")
    assert "Step review Step 2 — codex-review failed" in issues
    assert "transient-retries=5" in issues


def test_codex_failure_stages_vendor_diagnostics_in_implement_tmpdir(tmp_path: Path) -> None:
    impl = tmp_path / "implement"
    impl.mkdir()
    bin_dir = _stub_bin(
        tmp_path,
        "codex",
        "#!/usr/bin/env bash\nprintf 'vendor failure body\\n' >&2\nexit 1\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "codex", "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "fail"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "IMPLEMENT_TMPDIR": str(impl)},
    )
    assert proc.returncode == 1
    parts_dir = impl / "vendor-failure-diagnostics.parts"
    assert parts_dir.is_dir()
    assert any("vendor failure body" in part.read_text(encoding="utf-8") for part in parts_dir.iterdir())



def test_brainstorm_codex_auth_failure_uses_stderr_sink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sink = tmp_path / "codex-brainstorm-launch.failure.log"

    def auth_setup_failed(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (1, "codex auth setup failed")

    monkeypatch.setattr(_review_launcher, "_prepare_codex_home", auth_setup_failed)
    args = _codex_review_args(
        tmp_path,
        out_name="codex-brainstorm-output.txt",
        stderr_sink=str(sink),
        timing_task_kind="codex-brainstorm",
    )
    assert agents._review_launch_codex(args=args, prompt="hi") == 0
    sink_text = sink.read_text(encoding="utf-8")
    assert "STATUS=FAILED" in sink_text
    assert "codex auth setup failed" in sink_text


def test_brainstorm_cursor_failure_uses_stderr_sink_without_runlog_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "cursor-brainstorm-output.txt"
    sink = tmp_path / "cursor-brainstorm-launch.failure.log"
    append_called = {"value": False}

    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def run_with_retries_fail(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        out.with_suffix(out.suffix + ".diag").write_text("cursor brainstorm failed\n", encoding="utf-8")
        return (agents.RunExternalAgentResult(7, out), 1, 1)

    def append_launch_failure(**_kwargs: object) -> None:
        append_called["value"] = True

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(**_kwargs: object) -> None:
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def write_cursor_dirty_tree_from_baseline(**_kwargs: object) -> None:
        return None

    def record_timing(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(_review_launcher, "_review_write_cursor_dirty_tree_from_baseline", write_cursor_dirty_tree_from_baseline)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_fail)
    monkeypatch.setattr(_review_launcher, "_review_record_timing", record_timing)
    monkeypatch.setattr(_review_launcher, "_review_append_launch_failure", append_launch_failure)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink=str(sink),
        timing_task_kind="cursor-brainstorm",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 7
    assert append_called["value"] is False
    assert "cursor brainstorm failed" in sink.read_text(encoding="utf-8")


def test_review_cursor_failure_still_appends_runlog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "cursor-review-output.txt"
    sink = tmp_path / "cursor-review-launch.failure.log"
    append_called = {"value": False}

    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def run_with_retries_fail(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        out.with_suffix(out.suffix + ".diag").write_text("cursor review failed\n", encoding="utf-8")
        return (agents.RunExternalAgentResult(7, out), 1, 1)

    def append_launch_failure(**_kwargs: object) -> None:
        append_called["value"] = True

    monkeypatch.setattr(_review_launcher, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(_review_launcher, "cursor_preread_service_token", lambda: True)
    monkeypatch.setattr(_review_launcher, "cursor_auth_export_env", lambda: None)
    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(**_kwargs: object) -> None:
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def write_cursor_dirty_tree_from_baseline(**_kwargs: object) -> None:
        return None

    def record_timing(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(_review_launcher, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(_review_launcher, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(_review_launcher, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(_review_launcher, "_review_write_cursor_dirty_tree_from_baseline", write_cursor_dirty_tree_from_baseline)
    monkeypatch.setattr(_review_launcher, "_review_run_with_retries", run_with_retries_fail)
    monkeypatch.setattr(_review_launcher, "_review_record_timing", record_timing)
    monkeypatch.setattr(_review_launcher, "_review_append_launch_failure", append_launch_failure)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink=str(sink),
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args=args, original_prompt="hi") == 7
    assert append_called["value"] is True
    assert not sink.exists()


def _launch_review_argv_reject_case(
    tmp_path: Path,
    tool: str,
    extra_args: list[str],
    env: dict[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    out = tmp_path / "out.txt"
    return _run(["--tool", tool, "--output", str(out), "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi", *extra_args], env)


@pytest.mark.parametrize(
    ("tool", "extra_args", "env", "expected_rc"),
    [
        ("codex", ["--output", "/tmp/bad path/out.txt"], None, 1),
        ("codex", ["--stderr-sink", "/tmp/bad sink.log"], None, 1),
        ("codex", ["--timeout", "0"], None, 2),
        ("codex", ["--timeout", "abc"], None, 2),
        ("codex", ["--timing-task-kind", "--bogus"], None, 2),
        ("codex", ["--token-budget-cap", "0"], None, 2),
        ("codex", ["--token-budget-cap", "abc"], None, 2),
        ("codex", ["--timing-task-kind", "ok\nOUTER_LAUNCHER_WORKDIR=/tmp"], None, 2),
        ("codex", ["--risk", "high\nOUTER_LAUNCHER_WORKDIR=/tmp"], None, 2),
    ],
)
def test_launch_review_argv_reject_paths(
    tmp_path: Path,
    tool: str,
    extra_args: list[str],
    env: dict[str, str] | None,
    expected_rc: int,
) -> None:
    out = tmp_path / "out.txt"
    if extra_args and extra_args[0] == "--output":
        proc = _run(["--tool", tool, *extra_args, "--timeout", STUB_AGENT_TIMEOUT, "--prompt", "hi"], env)
    else:
        proc = _launch_review_argv_reject_case(tmp_path, tool, extra_args, env)
    assert proc.returncode == expected_rc
    assert not out.exists()


def test_launch_review_cli_cap_hit_skips_vendor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    vendor_called = {"value": False}

    def fake_run(argv: list[str], **_kwargs: object) -> object:
        if len(argv) >= 4 and argv[2:4] == ["token", "check-budget"]:
            return type("R", (), {"stdout": "STATUS=cap_hit TOTAL=42\n", "returncode": 0})()
        vendor_called["value"] = True
        return type("R", (), {"stdout": "", "returncode": 0})()

    monkeypatch.setattr(agents.proc, "run", fake_run)
    rc = agents.launch_review_main(
        ["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi", "--token-budget-cap", "10"],
    )
    assert rc == 0
    assert not vendor_called["value"]
    assert out.read_text(encoding="utf-8") == "STATUS=cap_hit\n"
    assert out.with_suffix(out.suffix + ".cap-hit").is_file()
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8") == "0\n"


def test_launch_review_cli_cap_hit_from_env_skips_vendor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    vendor_called = {"value": False}

    def fake_run(argv: list[str], **_kwargs: object) -> object:
        if len(argv) >= 4 and argv[2:4] == ["token", "check-budget"]:
            return type("R", (), {"stdout": "STATUS=cap_hit TOTAL=42\n", "returncode": 0})()
        vendor_called["value"] = True
        return type("R", (), {"stdout": "", "returncode": 0})()

    monkeypatch.setenv("LARCH_TOKEN_BUDGET_CAP_REVIEW", "10")
    monkeypatch.setattr(agents.proc, "run", fake_run)
    rc = agents.launch_review_main(
        ["--tool", "codex", "--output", str(out), "--timeout", "2", "--prompt", "hi"],
    )
    assert rc == 0
    assert not vendor_called["value"]
    assert out.read_text(encoding="utf-8") == "STATUS=cap_hit\n"
    assert out.with_suffix(out.suffix + ".cap-hit").is_file()


def test_codex_description_text_writes_full_prompt_sidecar(tmp_path: Path) -> None:
    rendered = "full rendered specialist prompt body"
    args = argparse.Namespace(
        agent_file="agents/code-reviewer.md",
        description_text="review this change",
        mode="review",
        scope_files="",
        competition_notice=False,
        competition_notice_file="",
        diff_file="",
        commit_count="",
        plan_file="",
        feature_file="",
    )
    output = tmp_path / "out.txt"
    sidecar = agents._review_write_codex_prompt_sidecar(output=output, prompt=rendered, args=args)
    text = sidecar.read_text(encoding="utf-8")
    assert text == rendered
    assert "LARCH_PROMPT_SENTINEL=1" not in text


def test_outer_meta_coerces_non_low_risk_to_high(tmp_path: Path) -> None:
    meta = tmp_path / "out.txt.meta"
    meta.write_text("", encoding="utf-8")
    prompt_sidecar = tmp_path / "out.txt.prompt"
    prompt_sidecar.write_text("hi", encoding="utf-8")
    agents._review_append_outer_meta(meta, prompt_sidecar=prompt_sidecar, risk="medium", stderr_sink="")
    assert "OUTER_LAUNCHER_RISK=high" in meta.read_text(encoding="utf-8")
    meta.write_text("", encoding="utf-8")
    agents._review_append_outer_meta(meta, prompt_sidecar=prompt_sidecar, risk="low", stderr_sink="")
    assert "OUTER_LAUNCHER_RISK=low" in meta.read_text(encoding="utf-8")
