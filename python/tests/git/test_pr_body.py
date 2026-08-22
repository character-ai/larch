"""Tests for pr_body.py."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from larch.core import config
from larch.git import pr_body


def test_sanitize_rejects_pipe_in_node() -> None:
    fragment = "flowchart LR\n  A[foo|bar] --> B\n"
    result = pr_body.sanitize_fragment(fragment)
    assert result.status == "rejected"
    assert config.MERMAID_REASON_PIPE_IN_NODE in result.reason_tokens


def test_sanitize_rejects_unclosed_frontmatter() -> None:
    fragment = "---\ntitle: x\nflowchart LR\n  A --> B\n"
    result = pr_body.sanitize_fragment(fragment)
    assert result.status == "rejected"
    assert config.MERMAID_REASON_UNCLOSED_FRONTMATTER in result.reason_tokens


def test_sanitize_fenced_mermaid_auto_extracts() -> None:
    fenced = "```mermaid\nflowchart LR\n  A --> B\n```\n"
    result = pr_body.sanitize_fragment(fenced)
    assert result.status == "ok"


def test_render_run_summary_includes_cost_line() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run1",
        total_cost="1.00",
        claude_cost="0.50",
        codex_cost="0.25",
        cursor_cost="0.10",
        claude_sub_cost="0.15",
        total_tokens=1000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    assert "💰 TOTAL" in body
    assert "**Cost**:" in body
    # Legacy callers passing only codex_cost still render the split (5.5 slot + $0.00 mini).
    assert "Codex-5.6 $0.25" in body
    assert "Codex-mini $0.00" in body
    assert "Claude $0.50" in body
    assert "Claude/GLM-5.2" not in body
    assert "**Cost note**:" not in body


def test_render_run_summary_needs_user_outcome_not_done() -> None:
    # #7074: a terminal needs-user ship handoff must not render as ✅ DONE even
    # though the outcome token stays pr-created.
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="pr-created",
        run_id="run1",
        needs_user_reason="architectural-assessments",
        needs_user_next_action="assessments",
        cost_unavailable=True,
    )
    outcome_line = next(line for line in body.splitlines() if "**Outcome**" in line)
    assert "✅ DONE" not in outcome_line
    assert "NEEDS USER" in outcome_line
    assert "architectural-assessments" in outcome_line
    assert "assessments" in outcome_line


def test_render_run_summary_pr_created_stays_done_without_handoff() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="pr-created",
        run_id="run1",
        cost_unavailable=True,
    )
    outcome_line = next(line for line in body.splitlines() if "**Outcome**" in line)
    assert outcome_line.strip() == "- **Outcome**: ✅ DONE"


def test_render_run_summary_glm_main_lane_plan_estimate() -> None:
    # Token Claude $15.00 → estimated $1.00; TOTAL replaces Claude with estimate:
    # 38.23 - 15.00 + 1.00 = 24.23
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run-glm",
        total_cost="38.23",
        claude_cost="15.00",
        codex_gpt_5_5_cost="11.24",
        codex_gpt_5_4_mini_cost="0.07",
        cursor_cost="8.09",
        claude_sub_cost="0.80",
        total_tokens=74240000,
        cost_unavailable=False,
        main_model="glm-5.2",
    )
    assert "Claude/GLM-5.2 token $15.00 (estimated $1.00)" in body
    assert "TOTAL ~$24.23" in body
    assert "Claude (subprocess) $0.80" in body
    assert "Codex-5.6 $11.24" in body
    cost_idx = body.index("- **Cost**:")
    note_idx = body.index("- **Cost note**:")
    issue_idx = body.index("- **Issue**:")
    assert cost_idx < note_idx < issue_idx
    assert "Token is API-equivalent GLM-5.2 pricing" in body
    assert "estimated is plan cost (token ÷ 15)" in body


def test_render_run_summary_glm_1m_alias_gets_plan_estimate() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run-glm-1m",
        total_cost="16.00",
        claude_cost="15.00",
        codex_cost="0.20",
        cursor_cost="0.30",
        claude_sub_cost="0.50",
        total_tokens=1000,
        cost_unavailable=False,
        main_model="glm-5.2[1m]",
    )
    assert "Claude/GLM-5.2 token $15.00 (estimated $1.00)" in body
    assert "TOTAL ~$2.00" in body  # 16 - 15 + 1
    assert "Claude (subprocess) $0.50" in body
    assert "**Cost note**:" in body


def test_render_run_summary_non_glm_1m_cost_line_is_byte_stable() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run-non-glm-1m",
        total_cost="16.00",
        claude_cost="15.00",
        codex_cost="0.20",
        cursor_cost="0.30",
        claude_sub_cost="0.50",
        total_tokens=1000,
        cost_unavailable=False,
        main_model="claude-opus-4-8[1m]",
    )
    cost_line = next(line for line in body.splitlines() if line.startswith("- **Cost**:"))
    assert cost_line == (
        "- **Cost**: 💰 TOTAL ~$16.00: Claude $15.00, Codex-5.6 $0.20, "
        "Codex-mini $0.00, Cursor $0.30, Claude (subprocess) $0.50  |  Tokens: 1k"
    )
    assert "Claude/GLM-5.2" not in body
    assert "**Cost note**:" not in body


def test_render_run_summary_glm_zero_cost_keeps_plan_formatting() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run-glm-zero",
        total_cost="0.00",
        claude_cost="0.00",
        codex_cost="0.00",
        cursor_cost="0.00",
        claude_sub_cost="0.00",
        total_tokens=0,
        cost_unavailable=False,
        main_model="glm-5.2",
    )
    assert "- **Cost**: 💰 TOTAL ~$0.00: Claude/GLM-5.2 token $0.00 (estimated $0.00)," in body
    assert "- **Cost note**:" in body


def test_render_run_summary_glm_cost_unavailable_omits_plan_formatting() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run-glm-unavailable",
        cost_unavailable=True,
        main_model="glm-5.2",
    )
    assert "- **Cost**: N/A" in body
    assert "Claude/GLM-5.2" not in body
    assert "**Cost note**:" not in body


def test_render_run_summary_splits_codex_by_model() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="completed",
        run_id="run1",
        total_cost="1.00",
        claude_cost="0.50",
        codex_cost="0.40",
        codex_gpt_5_5_cost="0.10",
        codex_gpt_5_4_mini_cost="0.30",
        cursor_cost="0.10",
        claude_sub_cost="0.00",
        total_tokens=1000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    assert "Codex-5.6 $0.10" in body
    assert "Codex-mini $0.30" in body
    assert "Codex $" not in body  # the old single-Codex slot is gone


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("merged", "✅ DONE"),
        ("approved", "✅ DONE"),
        ("stalled", "❌ STALLED"),
        ("bailed-needs-user-input", "bailed-needs-user-input"),
    ],
)
def test_map_outcome_display(outcome: str, expected: str) -> None:
    assert pr_body._map_outcome_display(outcome) == expected


def test_render_run_summary_emits_outcome_first_and_omits_mode() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="run1",
        workflow_path="post-plan",
        mode="merge",
        cost_unavailable=True,
    )
    lines = body.splitlines()

    assert lines[0] == "## /implement run run1: merged"
    assert lines[1] == ""
    assert lines[2] == "- **Outcome**: ✅ DONE"
    assert "- **Mode**:" not in body
    assert lines.index("- **Outcome**: ✅ DONE") < lines.index("- **Path**: post-plan")
    assert lines.index("- **Outcome**: ✅ DONE") < lines.index("- **Duration**: N/A")


def test_render_run_summary_main_emits_codex_model_split(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main([
        "--skill", "design", "--outcome", "approved", "--run-id", "r1",
        "--codex-input-tokens", "1000000", "--codex-output-tokens", "1000000",
        "--codex-mini-input-tokens", "1000000", "--codex-mini-output-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    assert "Codex-5.6 $" in body
    assert "Codex-mini $" in body


def test_render_run_summary_main_prices_claude_from_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"model_roster":{"main":"claude-sonnet-4-6"}}\n', encoding="utf-8")
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "completed", "--run-id", "r1",
        "--manifest-path", str(manifest),
        "--claude-input-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    assert "Claude $3.00" in body
    assert "- **Main agent model**: claude-sonnet-4-6" in body
    assert "Claude/GLM-5.2" not in body
    assert "**Cost note**:" not in body


def test_render_run_summary_main_glm_from_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"model_roster":{"main":"glm-5.2[1m]"}}\n', encoding="utf-8")
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "completed", "--run-id", "r-glm",
        "--manifest-path", str(manifest),
        "--claude-input-tokens", "1000000",
        "--claude-output-tokens", "1000000",
        "--claude-sub-input-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    # Token 5.80 → estimated 0.39; TOTAL = (5.80+5.00) - 5.80 + 0.39 = 5.39
    assert "Claude/GLM-5.2 token $5.80 (estimated $0.39)" in body
    assert "TOTAL ~$5.39" in body
    assert "Claude (subprocess) $5.00" in body
    assert "**Cost note**:" in body
    assert "- **Main agent model**: glm-5.2[1m]" in body


def test_render_run_summary_main_manifest_unknown_does_not_fallback_to_transcript(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"model_roster":{"main":"unknown"}}\n', encoding="utf-8")
    monkeypatch.setattr(pr_body.tokens, "read_main_model", lambda: "glm-5.2")

    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "completed", "--run-id", "r-unknown",
        "--manifest-path", str(manifest),
        "--claude-input-tokens", "1000000",
        "--print-stdout",
    ])

    assert rc == 0
    body = capsys.readouterr().out
    assert "Claude $5.00" in body
    assert "Claude/GLM-5.2" not in body
    assert "**Cost note**:" not in body
    assert "- **Main agent model**: unknown" in body


def test_render_run_summary_main_main_model_override_wins_for_pricing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text('{"model_roster":{"main":"claude-sonnet-4-6"}}\n', encoding="utf-8")
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "completed", "--run-id", "r1",
        "--manifest-path", str(manifest),
        "--main-model", "claude-haiku-4-5",
        "--claude-input-tokens", "1000000",
        "--print-stdout",
    ])
    assert rc == 0
    body = capsys.readouterr().out
    assert "Claude $1.00" in body
    assert "- **Main agent model**: claude-haiku-4-5" in body


def test_render_run_summary_includes_merge_downgrade_warning() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="pr-created",
        run_id="run1",
        pr_number="12",
        merge_downgraded="true",
        cost_unavailable=True,
    )

    assert "**⚠ Merge downgraded**" in body
    assert "panel-failed recovery shipped a PR without merging" in body


def test_render_run_summary_includes_dynamic_archetypes_line() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="pr-created",
        run_id="run1",
        dynamic_archetypes_line="static-only, pre-scouted-empty",
        cost_unavailable=True,
    )
    assert "- **Dynamic archetypes**: static-only, pre-scouted-empty" in body


@pytest.mark.parametrize("skill", ["implement", "design"])
def test_render_run_summary_never_emits_em_dash_in_bounded_block(skill: str) -> None:
    body = pr_body.render_run_summary(
        skill=skill,
        outcome="completed",
        run_id="run1",
        cost_unavailable=True,
    )
    block, sentinel, _tail = body.partition("<!-- larch:run-summary v=1 -->")
    assert sentinel == "<!-- larch:run-summary v=1 -->"
    assert "—" not in block


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--skill", "implement"],
        ["--skill", "bad", "--outcome", "x", "--run-id", "r"],
    ],
)
def test_render_run_summary_main_usage_errors(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main(argv)
    assert rc == 2
    captured = capsys.readouterr()
    assert "STATUS=ok" not in captured.err


def test_render_run_summary_main_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_file = tmp_path / "summary.md"
    rc = pr_body.render_run_summary_main([
        "--skill",
        "implement",
        "--outcome",
        "completed",
        "--run-id",
        "run-1",
        "--output-file",
        str(out_file),
        "--cost-unavailable",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "STATUS=ok" in captured.err
    assert f"OUTPUT_FILE={out_file}" in captured.err
    assert out_file.is_file()
    assert "run-1" in out_file.read_text(encoding="utf-8")


def test_render_run_summary_main_cost_unavailable(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main([
        "--skill",
        "design",
        "--outcome",
        "completed",
        "--run-id",
        "run-2",
        "--print-stdout",
        "--cost-unavailable",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "STATUS=ok" in captured.err
    assert "run-2" in captured.out


def test_diagram_failure_capture_redacts_prefixed_mermaid_on_stderr_line() -> None:
    diagnostic, tail = pr_body._diagram_failure_capture(returncode=1, stderr="ERROR graph TD A-->B")
    assert "graph TD" not in tail
    assert "A-->B" not in tail
    assert "diagram-content-redacted" in tail
    assert "graph TD" not in diagnostic
    assert "A-->B" not in diagnostic


def test_generate_code_flow_diagram_uses_launcher_not_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = tmp_path / "fake-launcher.sh"
    _ = launcher.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.setenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", str(launcher))
    raw_secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
    raw_stderr = f"timeout after 600s token={raw_secret}"

    def fake_run(*_args: object, **_kwargs: object) -> object:
        return type("R", (), {"returncode": 1, "stdout": "stdout diagnostic\n## Code Flow Diagram\n```mermaid\ngraph TD\nA-->B\n```", "stderr": raw_stderr})()

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    result = pr_body.generate_code_flow_diagram(tmp_path)
    assert result.exit_code == 1
    assert result.status == "failed"
    assert result.reason != "generation-failed"
    assert "generation-failed rc=1" in result.reason
    assert "tail=" in result.reason
    assert "timeout after 600s" in result.reason
    assert raw_secret not in result.reason
    failure_log = tmp_path / "code-flow-diagram.failure.log"
    assert failure_log.is_file()
    log_text = failure_log.read_text(encoding="utf-8")
    assert "exit-code=1" in log_text
    assert "timeout after 600s" in log_text
    assert "stdout diagnostic" in log_text
    assert "```" not in log_text
    assert "mermaid" not in log_text.lower()
    assert "A-->B" not in log_text
    assert raw_secret not in log_text
    assert not (tmp_path / "code-flow-diagram.raw-failure.log").exists()
    assert (tmp_path / "code-flow-prompt.md").is_file()


def test_generate_code_flow_diagram_labels_launcher_failure_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = tmp_path / "fake-launcher.sh"
    _ = launcher.write_text("#!/bin/sh\nexit 124\n", encoding="utf-8")
    launcher.chmod(0o755)
    monkeypatch.setenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", str(launcher))
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]

    def fake_run(*_args: object, **_kwargs: object) -> object:
        return subprocess.CompletedProcess(
            [],
            config.EXIT_TIMEOUT,
            stdout="STATUS=TIMEOUT\nLAUNCHER_FAILURE_CLASS=health\nLAUNCHER_FAILURE_REASON=auth\n",
            stderr="claude subprocess timed out\n",
        )

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    result = pr_body.generate_code_flow_diagram(tmp_path)

    assert result.exit_code == 1
    assert result.status == "failed"
    assert "generation-failed health/auth rc=124" in result.reason
    assert "tail=" in result.reason


def test_generate_code_flow_diagram_uses_rust_entrypoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    launch_argv: list[str] = []

    def fake_run(argv: list[str], **kwargs: object) -> object:
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(argv, 0, stdout="python/larch/git/pr_body.py\n", stderr="")
        if argv[1:3] == ["agent", "launch-claude-subprocess"]:
            launch_argv.extend(argv)
            output_file = Path(argv[argv.index("--output-file") + 1])
            _ = output_file.write_text(
                "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected argv")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)
    result = pr_body.generate_code_flow_diagram(tmp_path)

    assert result.exit_code == 0
    assert result.status == "ok"
    assert result.diagram_file
    assert result.reason == ""
    assert launch_argv[0] == str(
        pr_body.larch_entrypoint(Path(pr_body.__file__).resolve().parents[3])
    )
    assert launch_argv[1:3] == ["agent", "launch-claude-subprocess"]
    timeout_idx = launch_argv.index("--timeout")
    assert launch_argv[timeout_idx + 1] == str(pr_body._CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS)
    assert launch_argv[timeout_idx + 1] != "600"


def test_generate_code_flow_diagram_retries_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[1:3] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            output_file = Path(argv[argv.index("--output-file") + 1])
            if call_count == 1:
                # First attempt: timeout — write empty file, return EXIT_TIMEOUT
                _ = output_file.write_text("", encoding="utf-8")
                return subprocess.CompletedProcess(argv, config.EXIT_TIMEOUT, stdout="", stderr="")
            # Second attempt (first retry): success
            _ = output_file.write_text(
                "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    result = pr_body.generate_code_flow_diagram(tmp_path)

    assert call_count == 2, "should succeed on first retry"
    assert result.exit_code == 0
    assert result.status == "ok"
    assert result.diagram_file
    assert result.reason == ""
    assert (tmp_path / "code-flow-diagram.retried").is_file()
    retried_text = (tmp_path / "code-flow-diagram.retried").read_text(encoding="utf-8")
    assert f"FIRST_RC={config.EXIT_TIMEOUT}" in retried_text
    assert "RETRY_1_RC=0" in retried_text
    assert "RETRIES=1" in retried_text


def test_generate_code_flow_diagram_retries_on_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[1:3] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            output_file = Path(argv[argv.index("--output-file") + 1])
            if call_count == 1:
                # First attempt: launcher ran but produced empty output (No messages)
                _ = output_file.write_text("", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")
            # Second attempt (first retry): success
            _ = output_file.write_text(
                "## Code Flow Diagram\n\n```mermaid\nflowchart LR\n  A --> B\n```\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    result = pr_body.generate_code_flow_diagram(tmp_path)

    assert call_count == 2, "should succeed on first retry"
    assert result.exit_code == 0
    assert result.status == "ok"
    assert result.reason == ""
    assert (tmp_path / "code-flow-diagram.retried").is_file()


def test_generate_code_flow_diagram_no_retry_on_hard_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[1:3] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            # Hard failure: exit 1, no output file written
            return subprocess.CompletedProcess(argv, 1, stdout="launcher-init-failed", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    result = pr_body.generate_code_flow_diagram(tmp_path)

    assert call_count == 1, "should NOT retry when output file is absent"
    assert result.exit_code == 1
    assert result.status == "failed"
    assert not (tmp_path / "code-flow-diagram.retried").is_file()


def test_generate_code_flow_diagram_retries_up_to_max_on_persistent_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)
    monkeypatch.setattr(pr_body.time, "sleep", lambda _: None)  # type: ignore[arg-type]
    call_count = 0

    def fake_run(argv: list[str], **kwargs: object) -> object:
        nonlocal call_count
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[1:3] == ["agent", "launch-claude-subprocess"]:
            call_count += 1
            output_file = Path(argv[argv.index("--output-file") + 1])
            # Always fail with empty output (triggers retry)
            _ = output_file.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(argv, config.EXIT_TIMEOUT, stdout="", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    result = pr_body.generate_code_flow_diagram(tmp_path)

    expected_calls = 1 + pr_body._MAX_DIAGRAM_RETRIES
    assert call_count == expected_calls, f"should attempt {expected_calls} times total"
    assert result.exit_code == 1
    assert result.status == "failed"
    assert (tmp_path / "code-flow-diagram.retried").is_file()
    retried_text = (tmp_path / "code-flow-diagram.retried").read_text(encoding="utf-8")
    assert f"FIRST_RC={config.EXIT_TIMEOUT}" in retried_text
    assert f"RETRIES={pr_body._MAX_DIAGRAM_RETRIES}" in retried_text


def test_generate_code_flow_diagram_reads_stderr_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LARCH_TEST_LAUNCH_CLAUDE_SUBPROCESS", raising=False)

    auth_message = "takes precedence over your claude.ai login"
    raw_path = tmp_path / "code-flow-diagram.raw.md"

    def fake_run(argv: list[str], **kwargs: object) -> object:
        _ = kwargs
        if argv[:2] == ["git", "merge-base"]:
            return subprocess.CompletedProcess(argv, 0, stdout="abc123\n", stderr="")
        if argv[:3] == ["git", "diff", "--name-only"] or argv[:3] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(argv, 0, stdout="file.py\n", stderr="")
        if argv[1:3] == ["agent", "launch-claude-subprocess"]:
            # Write the .stderr sidecar as the real launcher would, leave stdout empty
            _ = raw_path.with_suffix(raw_path.suffix + ".stderr").write_text(auth_message + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 1, stdout="launcher-init-failed", stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr(pr_body.subprocess, "run", fake_run)  # type: ignore[arg-type]
    result = pr_body.generate_code_flow_diagram(tmp_path)

    assert result.exit_code == 1
    assert result.status == "failed"
    # Sidecar content must appear in the reason; completed.stderr was empty so
    # without Fix 1 the tail would be "no-output" instead.
    assert "claude.ai login" in result.reason


def test_render_run_summary_identity_lines_from_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    _ = manifest.write_text(
        json.dumps({"larch_version": "51.3.9", "model_roster": {"main": "claude-opus-4-8"}, "effort": "max"}),
        encoding="utf-8",
    )
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="R",
        manifest_path=str(manifest),
        cost_unavailable=True,
    )
    assert "- **Main agent model**: claude-opus-4-8" in body
    assert "- **Effort**: max" in body
    assert "- **Larch version**: 51.3.9" in body


def test_render_run_summary_identity_lines_explicit_override(tmp_path: Path) -> None:
    _ = tmp_path
    body = pr_body.render_run_summary(
        skill="design",
        outcome="planned",
        run_id="R",
        larch_version="50.0.0",
        main_model="claude-haiku-4-5",
        effort="high",
        cost_unavailable=True,
    )
    assert "- **Main agent model**: claude-haiku-4-5" in body
    assert "- **Effort**: high" in body
    assert "- **Larch version**: 50.0.0" in body


def test_render_run_summary_identity_lines_manifest_version_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_source = tmp_path / "plugin" / "python" / "larch" / "git" / "pr_body.py"
    fake_source.parent.mkdir(parents=True)
    plugin_json = tmp_path / "plugin" / ".claude-plugin" / "plugin.json"
    plugin_json.parent.mkdir()
    _ = plugin_json.write_text(json.dumps({"version": "52.7.3"}), encoding="utf-8")
    monkeypatch.setattr(pr_body, "__file__", str(fake_source), raising=False)

    body = pr_body.render_run_summary(
        skill="design",
        outcome="planned",
        run_id="R",
        main_model="claude-haiku-4-5",
        effort="high",
        cost_unavailable=True,
    )

    assert "- **Larch version**: 52.7.3" in body


def test_render_run_summary_cursor_lane_split_when_components_present() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="run1",
        total_cost="3.00",
        claude_cost="0.50",
        codex_cost="0.25",
        cursor_cost="2.00",
        cursor_composer_cost="1.20",
        cursor_grok_cost="0.60",
        claude_sub_cost="0.25",
        total_tokens=5000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    assert "Cursor $2.00 (Composer $1.20, Grok $0.60)" in body
    assert "Cursor $2.00" in body


def test_render_run_summary_cursor_aggregate_when_no_components() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="run1",
        total_cost="1.00",
        claude_cost="0.50",
        codex_cost="0.25",
        cursor_cost="0.10",
        claude_sub_cost="0.15",
        total_tokens=1000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    assert "Cursor $0.10" in body
    # Ensure no lane breakdown appears
    assert "Cursor $0.10 (Composer" not in body


def test_render_run_summary_cursor_lane_with_zero_valued_component() -> None:
    body = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="run1",
        total_cost="2.00",
        claude_cost="1.00",
        codex_cost="0.50",
        cursor_cost="0.30",
        cursor_composer_cost="0.30",
        cursor_grok_cost="0.00",
        claude_sub_cost="0.20",
        total_tokens=2000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    assert "Grok $0.00" in body
    assert "Auto $0.00" not in body


def test_render_run_summary_total_unchanged_by_cursor_split() -> None:
    body_aggregate = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="run1",
        total_cost="5.00",
        claude_cost="2.00",
        codex_cost="1.00",
        cursor_cost="1.50",
        claude_sub_cost="0.50",
        total_tokens=10000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    body_split = pr_body.render_run_summary(
        skill="implement",
        outcome="merged",
        run_id="run1",
        total_cost="5.00",
        claude_cost="2.00",
        codex_cost="1.00",
        cursor_cost="1.50",
        cursor_composer_cost="0.80",
        cursor_grok_cost="0.50",
        claude_sub_cost="0.50",
        total_tokens=10000,
        cost_unavailable=False,
        main_model="claude-opus-4-8",
    )
    assert "TOTAL ~$5.00" in body_aggregate
    assert "TOTAL ~$5.00" in body_split
    assert "10k" in body_aggregate
    assert "10k" in body_split


def test_render_run_summary_main_forwards_cursor_grok_flags(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "merged", "--run-id", "r1",
        "--cursor-grok-input-tokens", "1000000",
        "--cursor-grok-output-tokens", "1000000",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Grok" in out


def test_render_run_summary_main_grok_only_uses_detailed_pricing(capsys: pytest.CaptureFixture[str]) -> None:
    rc = pr_body.render_run_summary_main([
        "--skill", "implement", "--outcome", "merged", "--run-id", "r1",
        "--cursor-grok-input-tokens", "1000000",
        "--cursor-grok-cache-read-tokens", "0",
        "--cursor-grok-output-tokens", "1000000",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # Grok-only: detailed pricing activates; $8.00 = 1M@$2.00 input + 1M@$6.00 output
    assert "$8.00" in out
    assert "Grok" in out
