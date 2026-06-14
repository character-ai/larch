# pyright: reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for the Python review launcher."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import agents

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "python" / "cli.py"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update({
        "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT": "0",
        "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
        "LARCH_TRANSIENT_RETRY_DELAY": "0",
        "LARCH_CURSOR_LAUNCH_JITTER_MS": "0",
    })
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "agent", "launch-review", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=merged,
        timeout=10,
        check=False,
    )


def _codex_review_args(tmp_path: Path, out_name: str = "out.txt", **overrides: object) -> argparse.Namespace:
    out = tmp_path / out_name
    values: dict[str, object] = {
        "output": str(out),
        "timeout": "2",
        "codex_add_dir": "",
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
    sidecar = agents._review_write_codex_prompt_sidecar(output, prompt, args)
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
    assert agents._review_check_budget_or_write_cap_hit(output, 10, "codex-review")
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
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", "2", "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}"})
    assert proc.returncode == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert "CMD_JSON=[" in meta
    assert '"codex","exec","--sandbox","read-only"' in meta
    assert "OUTER_LAUNCHER=agent launch-review" in meta
    assert out.with_suffix(out.suffix + ".inner.done").exists() is False
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8") == "0\n"
    assert "REASON=codex-sandbox-read-only" in out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")


def test_cursor_launch_extracts_result_and_writes_original_prompt_sidecar(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        "#!/usr/bin/env bash\ncat <<'JSON'\n{\"result\":\"Reviewing... {\\\"no_issues_found\\\": true}\",\"usage\":{\"inputTokens\":1,\"outputTokens\":2,\"cacheReadTokens\":0,\"cacheWriteTokens\":0}}\nJSON\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"})
    assert proc.returncode == 0
    assert out.read_text(encoding="utf-8") == '{"no_issues_found": true}\n'
    assert out.with_suffix(out.suffix + ".prompt").read_text(encoding="utf-8") == "hi"
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert '"cursor","agent","-p","--trust","--mode","ask"' in meta
    assert "--api-key" not in meta
    assert "OUTER_LAUNCHER=agent launch-review" in meta


def test_codex_add_dir_rejects_outside_output(tmp_path: Path) -> None:
    out = tmp_path / "out.txt"
    outside = tmp_path.parent
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", "2", "--prompt", "hi", "--codex-add-dir", str(outside)])
    assert proc.returncode == 2
    assert not out.exists()


def test_codex_add_dir_rejects_missing_output_parent(tmp_path: Path) -> None:
    out = tmp_path / "missing" / "out.txt"
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", "2", "--prompt", "hi"])
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


def test_cursor_launch_writes_sidecar_ok_status(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        "#!/usr/bin/env bash\ncat <<'JSON'\n{\"result\":\"ok\",\"usage\":{\"inputTokens\":1,\"outputTokens\":2,\"cacheReadTokens\":0,\"cacheWriteTokens\":0}}\nJSON\n",
    )
    out = tmp_path / "out.txt"
    proc = _run(["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key"})
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
        real_write(path, text)

    monkeypatch.setattr(agents, "_write", track_write)
    agents._review_cursor_postprocess(output, 1)
    assert output.read_text(encoding="utf-8") == "atomic-result"
    assert any(text == "atomic-result" for _path, text in writes)


def test_cursor_empty_result_diag_is_redacted(tmp_path: Path) -> None:
    secret_path = f"/Users/testuser/larch3/session-{os.getpid()}"
    payload = json.dumps({"result": "", "usage": {"inputTokens": 1, "outputTokens": 0}, "request_id": secret_path})
    output = tmp_path / "out.txt"
    output.write_text(payload, encoding="utf-8")
    agents._review_cursor_postprocess(output, 1)
    diag = output.with_suffix(output.suffix + ".diag").read_text(encoding="utf-8")
    assert secret_path not in diag
    assert "<OPERATOR_REPO_PATH>" in diag


def test_codex_auth_setup_preflight_exits_zero_with_clean_dirty_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _codex_review_args(tmp_path)
    out = Path(args.output)
    def auth_setup_failed(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (1, "codex auth setup failed")

    monkeypatch.setattr(agents, "_prepare_codex_home", auth_setup_failed)
    rc = agents._review_launch_codex(args, "hi")
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

    monkeypatch.setattr(agents, "_prepare_codex_home", auth_setup_failed)
    assert agents._review_launch_codex(args, "hi") == 0
    meta = out.with_suffix(out.suffix + ".meta").read_text(encoding="utf-8")
    assert f"STDERR_SINK={sink}" in meta
    assert "OUTER_LAUNCHER_STDERR_SINK" not in meta


def test_codex_sentinel_replays_with_ns_retry_header_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ns_header = "IMPORTANT: structured output required\n\n"
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
    sidecar = agents._review_write_codex_prompt_sidecar(output, prompt, args)
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

    monkeypatch.setattr(agents, "run_external_agent", fake_run)
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

    monkeypatch.setattr(agents, "run_external_agent", fake_run)
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


def test_review_serial_lock_releases_before_blocking_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    order: list[str] = []

    def fake_acquire(_tool: str) -> agents.SerialLockState:
        order.append("acquire")
        return agents.SerialLockState(None)

    def fake_release(_state: agents.SerialLockState) -> None:
        order.append("release")

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        order.append("run")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setattr(agents, "external_serial_lock_acquire", fake_acquire)
    monkeypatch.setattr(agents, "external_serial_lock_release_after", fake_release)
    monkeypatch.setattr(agents, "run_external_agent", fake_run)
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
    agents._review_cursor_postprocess(json_sidecar, 1)
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

    monkeypatch.setattr(agents, "_prepare_codex_home", auth_setup_ok)
    monkeypatch.setattr(agents, "_review_run_with_retries", run_with_retries_ok)
    assert agents._review_launch_codex(args, "hi") == 0
    assert out.with_suffix(out.suffix + ".token-record").is_file()
    assert ("token", "record-vendor-sidecar") in calls
    assert ("token", "record-vendor") not in calls


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
    proc = _run(["--tool", "codex", "--output", str(out), "--timeout", "2", "--prompt", "hi"], {"PATH": f"{bin_dir}:{os.environ['PATH']}"})
    assert proc.returncode == 0
    assert state.read_text(encoding="utf-8").strip() == "2"
    assert out.read_text(encoding="utf-8") == "OK"


def test_cursor_auth_preflight_writes_preflight_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "out.txt"
    def cursor_auth_missing(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=False, rc=1, message="cursor auth missing")

    monkeypatch.setattr(
        agents,
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
    assert agents._review_launch_cursor(args, "hi") == 1
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
        ["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi"],
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

    monkeypatch.setattr(agents, "_review_record_timing", track_timing)
    monkeypatch.setattr(agents, "_promote_inner_done", track_promote)
    def cursor_auth_ok(*, caller: str = "agent cursor-auth-preflight") -> agents.AuthVerdict:
        _ = caller
        return agents.AuthVerdict(ok=True, rc=0, message="")

    def setup_cursor_config_dir() -> tuple[Path, str | None]:
        return (tmp_path / "cfg", None)

    def cleanup_cursor_config_dir(_cfg_tmp: Path, _old_cfg: str | None) -> None:
        return None

    def capture_cursor_dirty_baseline(_output: Path) -> Path:
        return tmp_path / "baseline"

    def write_cursor_dirty_tree_from_baseline(_output: Path, _baseline: Path) -> None:
        return None

    def cursor_postprocess(_output: Path, _transient_attempt: int) -> None:
        return None

    def run_with_retries_ok(**_kwargs: object) -> tuple[agents.RunExternalAgentResult, int, int]:
        return (agents.RunExternalAgentResult(0, out), 1, 1)

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    monkeypatch.setattr(agents, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(agents, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(agents, "_review_capture_cursor_dirty_baseline", capture_cursor_dirty_baseline)
    monkeypatch.setattr(agents, "_review_write_cursor_dirty_tree_from_baseline", write_cursor_dirty_tree_from_baseline)
    monkeypatch.setattr(agents, "_review_cursor_postprocess", cursor_postprocess)
    monkeypatch.setattr(agents, "_review_run_with_retries", run_with_retries_ok)
    monkeypatch.setattr(agents, "resolve_model_args", resolve_model_args_ok)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args, "hi") == 0
    assert order == ["timing", "done"]


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True, text=True)
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


def test_codex_model_args_preflight_exit_one_with_unknown_dirty_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    args = _codex_review_args(tmp_path)

    def prepare_ok(_home_dir: Path, *, trusted_instructions_file: str = "") -> tuple[int, str]:
        _ = trusted_instructions_file
        return (0, "")

    def model_args_fail(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        raise ValueError("bad codex model")

    monkeypatch.setattr(agents, "_prepare_codex_home", prepare_ok)
    monkeypatch.setattr(agents, "resolve_model_args", model_args_fail)
    out = Path(args.output)
    assert agents._review_launch_codex(args, "hi") == 1
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

    monkeypatch.setattr(agents, "resolve_model_args", model_args_fail)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args, "hi") == 1
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=unknown" in dirty
    assert "model-args-preflight-no-agent-ran" in dirty
    assert out.with_suffix(out.suffix + ".done").read_text(encoding="utf-8").strip() == "1"
    assert "load_model_args failed" in out.with_suffix(out.suffix + ".diag").read_text(encoding="utf-8")


def test_invalid_token_budget_cap_zero_still_runs_vendor(tmp_path: Path) -> None:
    bin_dir = _stub_bin(
        tmp_path,
        "cursor",
        '#!/usr/bin/env bash\ncat <<\'JSON\'\n{"result":"ok","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\nJSON\n',
    )
    out = tmp_path / "out.txt"
    proc = _run(
        ["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi"],
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
        ["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi"],
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

    def cleanup_cursor_config_dir(_cfg_tmp: Path, _old_cfg: str | None) -> None:
        return None

    def resolve_model_args_ok(_tool: str, *, with_effort: bool = False, default_model: str = "") -> agents.ModelArgResult:
        _ = (with_effort, default_model)
        return agents.ModelArgResult(())

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        out.write_text('{"result":"ok","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, out)

    monkeypatch.chdir(repo)
    monkeypatch.setattr(agents, "cursor_auth_preflight", cursor_auth_ok)
    monkeypatch.setattr(agents, "cursor_preread_service_token", lambda: None)
    monkeypatch.setattr(agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(agents, "_review_setup_cursor_config_dir", setup_cursor_config_dir)
    monkeypatch.setattr(agents, "_review_cleanup_cursor_config_dir", cleanup_cursor_config_dir)
    monkeypatch.setattr(agents, "resolve_model_args", resolve_model_args_ok)
    monkeypatch.setattr(agents, "run_external_agent", fake_run)
    args = argparse.Namespace(
        output=str(out),
        timeout="2",
        risk="",
        stderr_sink="",
        timing_task_kind="cursor-review",
        token_budget_cap="",
    )
    assert agents._review_launch_cursor(args, "hi") == 0
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
    baseline = agents._review_capture_cursor_dirty_baseline(out)
    (repo / "reviewer-new.txt").write_text("reviewer\n", encoding="utf-8")
    agents._review_write_cursor_dirty_tree_from_baseline(out, baseline)
    dirty = out.with_suffix(out.suffix + ".dirty-tree").read_text(encoding="utf-8")
    assert "STATUS=dirty" in dirty
    new_untracked = out.with_suffix(out.suffix + ".dirty-tree.new-untracked-paths")
    assert new_untracked.is_file()
    assert b"reviewer-new.txt" in new_untracked.read_bytes()


def test_cursor_empty_result_retries_with_lock_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "out.txt"
    calls = {"count": 0, "locks": 0}

    def fake_acquire(_tool: str) -> agents.SerialLockState:
        calls["locks"] += 1
        return agents.SerialLockState(None)

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        if calls["count"] == 1:
            output.write_text('{"result":"","usage":{"inputTokens":1,"outputTokens":0}}\n', encoding="utf-8")
        else:
            output.write_text('{"result":"ok","usage":{"inputTokens":1,"outputTokens":2}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setenv("LARCH_CURSOR_RETRY_EMPTY_RESULT", "1")
    monkeypatch.setattr(agents, "external_serial_lock_acquire", fake_acquire)
    monkeypatch.setattr(agents, "external_serial_lock_release_after", lambda _state: None)
    monkeypatch.setattr(agents, "run_external_agent", fake_run)
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

    def fake_acquire(_tool: str) -> agents.SerialLockState:
        calls["locks"] += 1
        return agents.SerialLockState(None)

    def fake_run(**_kwargs: object) -> agents.RunExternalAgentResult:
        calls["count"] += 1
        output.write_text('{"result":"","usage":{"inputTokens":1,"outputTokens":0}}\n', encoding="utf-8")
        return agents.RunExternalAgentResult(0, output)

    monkeypatch.setenv("LARCH_CURSOR_RETRY_EMPTY_RESULT", "0")
    monkeypatch.setattr(agents, "external_serial_lock_acquire", fake_acquire)
    monkeypatch.setattr(agents, "external_serial_lock_release_after", lambda _state: None)
    monkeypatch.setattr(agents, "run_external_agent", fake_run)
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

    monkeypatch.setattr(agents, "run_external_agent", fake_run)
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
        ["--tool", "cursor", "--output", str(out), "--timeout", "2", "--prompt", "hi"],
        {"PATH": f"{bin_dir}:{os.environ['PATH']}", "CURSOR_API_KEY": "test-key", "LARCH_CURSOR_RETRY_EMPTY_RESULT": "1"},
    )
    assert proc.returncode == 0
    assert state.read_text(encoding="utf-8").strip() == "2"
    assert out.read_text(encoding="utf-8") == "ok"


def test_cursor_postprocess_tolerates_invalid_output_tokens(tmp_path: Path) -> None:
    output = tmp_path / "out.txt"
    payload = '{"result":"ok","usage":{"inputTokens":1,"outputTokens":"not-a-number"}}'
    output.write_text(payload, encoding="utf-8")
    agents._review_cursor_postprocess(output, 1)
    assert output.read_text(encoding="utf-8") == "ok"
