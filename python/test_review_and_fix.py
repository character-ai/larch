# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnknownLambdaType=false
# ruff: noqa: ARG005
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest import mock

import logging_util
import pytest
import checks
import review_and_fix
from _pytest.mark.structures import Mark, MarkDecorator


def _mark(name: str) -> MarkDecorator:
    return MarkDecorator(Mark(name, (), {}, _ispytest=True), _ispytest=True)


MARK_CHECK_CHANGES = _mark("check_changes")
MARK_CONVERGENCE = _mark("convergence")
MARK_DISPATCH = _mark("dispatch")
MARK_LOOP_TIMING = _mark("loop_timing")
MARK_PARSERS = _mark("parsers")
MARK_STARTING_ROUND = _mark("starting_round")
MARK_STEP5 = _mark("step5")
MARK_WRITE_REJECTED = _mark("write_rejected")


def _tmp_impl(tmp_path: Path) -> Path:
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "session-env.sh").write_text(
        "RUN_ID=run-1\nCODEX_PRESENT=false\nCURSOR_PRESENT=false\nLARCH_CLAUDE_PLUGIN_ROOT=/tmp/plugin\n",
        encoding="utf-8",
    )
    (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    (impl / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    return impl


def test_review_core_capture_captures_stdout_emit_and_restores_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", "old")
    env_path = tmp_path / "round-1" / "review-core.env"

    def fake_core(argv: list[str]) -> int:
        assert "--round-num" in argv
        print("PRINTED=1")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        assert os.environ["IMPLEMENT_TMPDIR"] == str(tmp_path)
        return 0

    rc = review_and_fix.review_core_capture(["--round-num", "1"], env_path, fake_core, tmp_path)

    assert rc == 0
    assert "PRINTED=1" in env_path.read_text(encoding="utf-8")
    assert "REVIEW_CORE_STATUS=ok" in env_path.read_text(encoding="utf-8")
    assert os.environ["IMPLEMENT_TMPDIR"] == "old"


@MARK_PARSERS
def test_step5_single_emits_round_kvs_without_review_core_leak(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    monkeypatch.setattr(review_and_fix.review_pipeline, "review_core", fake_core)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "single", "--round-num", "1"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEW_AND_FIX_STATUS=complete" in out
    assert "REVIEW_CORE_STATUS=ok" in out
    assert "ROUND_NUM=1" in out
    assert "REVIEW_CORE_STATUS=ok\nACCEPTED_COUNT" not in out
    assert (impl / "round-1" / "review-core.env").is_file()
    assert (impl / "progress" / "done").is_file()


@MARK_LOOP_TIMING
def test_step5_loop_emits_single_final_envelope(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_core(argv: list[str]) -> int:
        out_dir = Path(argv[argv.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        logging_util.emit("REVIEW_CORE_STATUS=ok")
        logging_util.emit("ACCEPTED_COUNT=0")
        logging_util.emit("REJECTED_COUNT=0")
        logging_util.emit(f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}")
        logging_util.emit(f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}")
        return 0

    monkeypatch.setattr(review_and_fix.review_pipeline, "review_core", fake_core)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])

    out = capsys.readouterr().out
    assert rc == 0
    assert out.count("STEP5_REVIEW_STATUS=") == 1
    assert "STEP5_REVIEW_STATUS=complete" in out
    assert "EFFECTIVE_ROUND_CAP=5" in out
    assert not any(line.startswith("REVIEW_AND_FIX_STATUS=") for line in out.splitlines())


@MARK_DISPATCH
def test_apply_findings_empty_file_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    findings = tmp_path / "findings.md"
    findings.write_text("", encoding="utf-8")
    rc = review_and_fix.apply_findings(["--findings-file", str(findings), "--review-tmpdir", str(tmp_path / "review")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEW_AND_FIX_STATUS=no-findings" in out
    assert "CODER_STATUS=skipped" in out


@MARK_CHECK_CHANGES
def test_check_changes_parse_error_stable_kvs(monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    rc = review_and_fix.check_changes(["--bogus"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines() == [
        "FILES_CHANGED=false",
        "UNTRACKED_BASELINE=missing",
        "GIT_PROBE_FAILED=false",
    ]


@MARK_WRITE_REJECTED
def test_write_rejected_counts_and_copies(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "rejected-findings.md").write_text("### [Code Review] One\nbody\n", encoding="utf-8")
    rc = review_and_fix.write_rejected([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-1",
        "--log-root", str(tmp_path / "logs"),
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REJECTED_COUNT=1" in out
    assert "STATUS=ok" in out
    assert (tmp_path / "logs" / "implement" / "run-1" / "rejected-findings.md").is_file()


def test_review_and_fix_source_uses_in_process_review_core():
    source = Path(review_and_fix.__file__).read_text(encoding="utf-8")
    assert '"review", "core"' not in source
    assert "python/cli.py review core" not in source
    assert "review_core_capture" in source
    assert "--prune-ledger" in source


@MARK_DISPATCH
def test_compose_coder_prompt_uses_canonical_submodule_prohibition(tmp_path):
    submodules = ["vendor/foo"]
    body = review_and_fix._compose_coder_prompt(tmp_path / "prompt.md", tmp_path / "f.md", tmp_path, submodules)
    assert "Do NOT read, edit, create, delete, move" in body
    assert "Do NOT touch `.git/`" in body


@MARK_DISPATCH
def test_resolve_coder_timing_ledger_round_and_flat_layouts(tmp_path: Path) -> None:
    assert review_and_fix._resolve_coder_timing_ledger(tmp_path / "round-1") == tmp_path / "timing-ledger.tsv"
    flat = tmp_path / "review-flat"
    assert review_and_fix._resolve_coder_timing_ledger(flat) == flat / "timing-ledger.tsv"


@MARK_DISPATCH
def test_run_coder_codex_rejects_nonzero_launcher_exit(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_PRESENT", "true")
    monkeypatch.setattr(review_and_fix, "_codex_available", lambda: True)
    output = tmp_path / "coder-codex.log"
    output.write_text("ok\n", encoding="utf-8")

    def fake_run(_argv, **_kwargs):
        class Result:
            returncode = 0
            stdout = "LAUNCHER_EXIT=1\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    assert review_and_fix._run_coder_codex(tmp_path, "prompt", tmp_path / "tool.log") is False


@MARK_DISPATCH
def test_run_coder_codex_exports_resolved_timing_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    output = round_dir / "coder-codex.log"
    output.write_text("ok\n", encoding="utf-8")
    seen_env: dict[str, str] = {}
    monkeypatch.setenv("CODEX_BINARY_FOUND", "true")
    monkeypatch.setattr(review_and_fix, "_codex_available", lambda: True)

    def fake_run(argv: list[str], **kwargs: object) -> review_and_fix.proc.CommandResult:
        seen_env.update(kwargs.get("env") or {})  # type: ignore[arg-type]
        return review_and_fix.proc.CommandResult(tuple(argv), 0, "LAUNCHER_EXIT=0\n", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)

    assert review_and_fix._run_coder_codex(round_dir, "prompt", round_dir / "tool.log") is True
    assert seen_env["LARCH_TIMING_LEDGER"] == str(tmp_path / "timing-ledger.tsv")
    assert seen_env["IMPLEMENT_TMPDIR"] == str(tmp_path)


@MARK_DISPATCH
def test_dynamic_archetypes_defaults_to_three_with_implement_tmpdir(monkeypatch, tmp_path):
    monkeypatch.delenv("LARCH_DYNAMIC_ARCHETYPES_MAX", raising=False)
    impl = _tmp_impl(tmp_path)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args, impl) == "3"



@MARK_DISPATCH
def test_dynamic_archetypes_uses_exported_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LARCH_DYNAMIC_ARCHETYPES_MAX", "2")
    impl = _tmp_impl(tmp_path)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args, impl) == "2"


def test_step5_shell_exports_validated_dynamic_cap_before_exec() -> None:
    text = (Path(__file__).resolve().parents[1] / "skills/implement/scripts/step-5-review.sh").read_text(encoding="utf-8")
    validation = 'case "$dynamic_archetypes_cap" in [0-3])'
    export = 'export LARCH_DYNAMIC_ARCHETYPES_MAX="$dynamic_archetypes_cap"'
    banner = "dynamic-archetypes cap=%s"
    exec_line = "exec python3"
    assert validation in text
    assert export in text
    assert text.index(validation) < text.index(export) < text.index(banner) < text.index(exec_line)

@MARK_DISPATCH
def test_dynamic_archetypes_defaults_to_zero_without_implement_tmpdir(monkeypatch, tmp_path):
    monkeypatch.delenv("LARCH_DYNAMIC_ARCHETYPES_MAX", raising=False)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args, tmp_path / "missing") == "0"


@MARK_DISPATCH
def test_post_dispatch_submodule_revert_restores_tracked_path_with_trailing_slash(tmp_path, monkeypatch):
    sub = tmp_path / "vendor"
    sub.mkdir()
    (sub / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    monkeypatch.setattr(review_and_fix, "_capture_round_tracked_paths", lambda: ["vendor/tracked.txt"])
    monkeypatch.setattr(review_and_fix, "_capture_round_untracked_paths", list)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0))
    count = review_and_fix._post_dispatch_submodule_revert(round_dir, ["vendor"])
    assert count == 1


@MARK_STEP5
def test_step5_handoff_envelope_uses_false_stall_tracking(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0, "coder-main-agent-required", "fix-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(4, status="main-agent-required"),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=coder-main-agent-required" in out
    assert "STALL_TRACKING=false" in out


@MARK_STARTING_ROUND
def test_step5_starting_round_missing_prior_emits_invalid(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "3", "--round-cap", "5",
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=starting-round-invalid" in out


@MARK_STARTING_ROUND
def test_step5_resume_past_cap_with_prior_artifact(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    prior = impl / "round-5" / "review-and-fix.env"
    prior.parent.mkdir(parents=True)
    prior.write_text("REVIEW_AND_FIX_STATUS=main-agent-vote-required\n", encoding="utf-8")
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "6", "--round-cap", "5",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=mav-resume-past-cap" in out


@MARK_STEP5
def test_mav_apply_writes_relocated_pre_coder_head_only(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    findings = impl / "accepted.md"
    findings.write_text("### FINDING_1: x\n- **Severity**: nit\n", encoding="utf-8")
    monkeypatch.setattr(review_and_fix, "apply_findings_with_coder", lambda *a, **k: review_and_fix.CoderResult(0, status="no-changes"))
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "abc123")
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "mav-apply", "--round-num", "1", "--findings-file", str(findings),
    ])
    snap = review_and_fix.pre_coder_snapshot_dir(impl / "round-1")
    assert rc == 0
    assert (snap / "pre-coder-head.txt").is_file()
    assert not (snap / "pre-coder-tracked-paths.txt").exists()
    assert not (snap / "pre-coder-untracked-paths.txt").exists()
    assert not (impl / "round-1" / "pre-coder-head.txt").exists()


@MARK_WRITE_REJECTED
def test_write_rejected_redacts_tmpdir_and_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    secret = "sk-" + "a" * 40
    (impl / "rejected-findings.md").write_text(f"### [Code Review] One\n{tmp_path}/secret {secret}\n", encoding="utf-8")
    rc = review_and_fix.write_rejected([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-1",
        "--log-root", str(tmp_path / "logs"),
    ])
    dest = tmp_path / "logs" / "implement" / "run-1" / "rejected-findings.md"
    text = dest.read_text(encoding="utf-8")
    assert rc == 0
    assert secret not in text
    assert "<REDACTED-TOKEN>" in text


@MARK_PARSERS
def test_step5_checks_result_capture_maps_ok_fields():
    parsed = review_and_fix._checks_result_capture(
        review_and_fix.checks.ChecksResult(
            ok=True,
            exit_code=0,
            site="step5-review-fixes",
            redacted_log_path=None,
            phase="unknown",
            coverage="full",
            skipped=False,
            warn=None,
        )
    )
    assert parsed["RELEVANT_CHECKS_OK"] == "true"
    assert parsed["COVERAGE"] == "full"


@MARK_CONVERGENCE
def test_step5_post_round_substantial_at_cap_emits_cap_hit(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    snap = review_and_fix.pre_coder_snapshot_dir(round_dir)
    snap.mkdir(parents=True)
    (snap / "pre-coder-head.txt").write_text("head\n", encoding="utf-8")
    (round_dir / "post-coder-head.txt").write_text("head\n", encoding="utf-8")
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: a **Important**\n### FINDING_2: b **Important**\n", encoding="utf-8")
    result = review_and_fix.RoundResult(
        0, "fix-applied", "fix-required", 1, 2, 0, 0, 0, 2, 0, 0, 0,
        accepted, round_dir / "rejected-findings.md", round_dir,
        impl / "review-and-fix-summary.json", impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, input_count=2, status="applied"),
    )
    monkeypatch.setattr(review_and_fix, "_run_relevant_checks_captured", lambda impl_tmpdir: {"STATUS": "pass", "RELEVANT_CHECKS_OK": "true"})
    status, _reason, cont = review_and_fix._step5_post_round_gates(result, 5, 5, impl)
    assert status == "cap-hit"
    assert cont is False


@MARK_DISPATCH
def test_process_skipped_findings_routes_security_vs_oos(tmp_path):
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    in_scope = round_dir / "accepted-in-scope-findings.md"
    in_scope.write_text("### FINDING_1: [security] x\n- focus-area: security\n", encoding="utf-8")
    coder_log = round_dir / "coder-output.log"
    coder_log.write_text("SKIPPED: FINDING_1\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    count, failed = review_and_fix._process_skipped_findings(round_dir, in_scope, coder_log, impl)
    assert failed is False
    assert count == 1
    assert (round_dir / "skipped-findings.security.md").stat().st_size > 0
    assert not (impl / "accumulated-oos.md").exists()


@MARK_DISPATCH
def test_process_skipped_findings_mirrors_security_aggregate_across_rounds(tmp_path):
    impl = tmp_path / "impl"
    impl.mkdir()
    for round_num, finding_id in ((1, "FINDING_1"), (2, "FINDING_2")):
        round_dir = impl / f"round-{round_num}"
        round_dir.mkdir()
        in_scope = round_dir / "accepted-in-scope-findings.md"
        in_scope.write_text(f"### {finding_id}: [security] x\n- focus-area: security\n", encoding="utf-8")
        coder_log = round_dir / "coder-output.log"
        coder_log.write_text(f"SKIPPED: {finding_id}\n", encoding="utf-8")
        count, failed = review_and_fix._process_skipped_findings(round_dir, in_scope, coder_log, impl)
        assert failed is False
        assert count == 1
    aggregate = (impl / "skipped-security-findings.md").read_text(encoding="utf-8")
    assert "FINDING_1" in aggregate
    assert "FINDING_2" in aggregate
    assert not (impl / "accumulated-oos.md").exists()


@MARK_STEP5
def test_step5_loop_preflight_empty_plan_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "plan.txt").write_text("", encoding="utf-8")
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out


@MARK_STEP5
def test_step5_mav_apply_missing_findings_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5([
        "--implement-tmpdir", str(impl), "--mode", "mav-apply", "--round-num", "1",
        "--findings-file", str(impl / "missing.md"),
    ])
    assert rc == 2


@MARK_STEP5
def test_step5_main_agent_vote_emits_ledger_kvs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0, "main-agent-vote-required", "main-agent-vote-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_LEDGER_READY=true" in out
    assert "STEP5_REVIEW_LEDGER_SITE=step5-mav" in out
    assert "STEP5_REVIEW_LEDGER_TRIGGER=main-agent-vote-required" in out


@MARK_STEP5
def test_step5_handoff_returns_zero_when_core_rc_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            2, "main-agent-vote-required", "main-agent-vote-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=main-agent-vote-required" in out
    assert "STEP5_REVIEW_LEDGER_EXIT_CODE=0" in out


@MARK_LOOP_TIMING
def test_step5_handoff_persists_round_start_without_timing(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    timing_calls: list[list[str]] = []

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            0, "main-agent-vote-required", "main-agent-vote-required", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda argv: timing_calls.append(argv) or 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    assert rc == 0
    assert not timing_calls
    assert (impl / "round-1" / "round-start-s").is_file()


@MARK_STEP5
def test_step5_invalid_dynamic_archetypes_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("LARCH_DYNAMIC_ARCHETYPES_MAX", "9")
    impl = _tmp_impl(tmp_path)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out


@MARK_STEP5
def test_record_escalation_failure_appends_tool_failure(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    stderr_path = impl / "round-1" / "review-and-fix.stderr"
    stderr_path.parent.mkdir(parents=True)
    stderr_path.write_text("boom\n", encoding="utf-8")

    def fail_helper(_argv, **_kwargs):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "record failed"

        return Result()

    monkeypatch.setattr(review_and_fix, "_run", fail_helper)
    review_and_fix._record_escalation_if_needed(impl, "coder-main-agent-required", 2, stderr_path)
    text = (impl / "execution-issues.md").read_text(encoding="utf-8")
    assert "Tool Failure: record-escalation" in text


@MARK_WRITE_REJECTED
def test_write_rejected_findings_aggregate_multi_round(tmp_path):
    impl = tmp_path / "impl"
    impl.mkdir()
    r1 = impl / "round-1"
    r2 = impl / "round-2"
    r1.mkdir()
    r2.mkdir()
    (r1 / "rejected-findings-full.md").write_text("### FINDING_1: A\nbody\n", encoding="utf-8")
    (r2 / "rejected-findings-full.md").write_text("### FINDING_2: B\nbody\n", encoding="utf-8")
    review_and_fix.write_rejected_findings_aggregate(impl)
    text = (impl / "rejected-findings.md").read_text(encoding="utf-8")
    assert "# Review Round 1" in text
    assert "# Review Round 2" in text
    assert "FINDING_1" in text
    assert "FINDING_2" in text


@MARK_CONVERGENCE
def test_fix_applied_not_rewritten_to_converged_before_gates(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: nit only\n- **Severity**: nit\n", encoding="utf-8")
    (round_dir / "findings.md").write_text("### FINDING_1: nit only\n", encoding="utf-8")

    def fake_capture(core_args, core_out, **_kwargs):
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        if accepted.resolve() != (out_dir / "accepted-findings.md").resolve():
            shutil.copyfile(accepted, out_dir / "accepted-findings.md")
        (out_dir / "findings.md").write_text("### FINDING_1: nit only\n", encoding="utf-8")
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=fix-required",
                "ACCEPTED_COUNT=1",
                "REJECTED_COUNT=0",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(review_and_fix, "review_core_capture", fake_capture)
    monkeypatch.setattr(review_and_fix, "apply_findings_with_coder", lambda *a, **k: review_and_fix.CoderResult(0, status="applied", input_count=1))
    monkeypatch.setattr(review_and_fix, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(review_and_fix, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "1", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.status == "fix-applied"


@pytest.mark.record_timing
def test_record_round_timing_writes_ledger_row(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir()
    (round_dir / "accepted-findings.md").write_text("### FINDING_1: x\n", encoding="utf-8")
    rc = review_and_fix.record_round_timing([
        "--implement-tmpdir", str(impl), "--round", "1", "--start-s", "100", "--end-s", "200",
    ])
    assert rc == 0
    assert (impl / "timing-ledger.tsv").is_file()


def test_write_self_review_tally_emits_step5_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    rc = review_and_fix.write_self_review_tally([
        "--implement-tmpdir", str(impl),
        "--run-id", "run-sr",
        "--accepted", "0",
        "--rejected", "0",
    ])
    assert rc == 0
    run_dir = impl / "larch-logs" / "implement" / "run-sr"
    tally_path = run_dir / "code-review-tally.json"
    assert tally_path.is_file()
    tally = json.loads(tally_path.read_text(encoding="utf-8"))
    assert tally["phase"] == "code-review"
    assert tally["mode"] == "self-review"
    assert tally["rounds"] == 1
    assert tally["accepted_count"] == 0
    assert tally["rejected_count"] == 0
    findings_path = run_dir / "review-findings-full.jsonl"
    assert findings_path.is_file()
    assert findings_path.read_text(encoding="utf-8") == ""


@pytest.mark.commit_fixes
def test_commit_fixes_emits_committed_kv(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(_tmp_impl(tmp_path)))
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0))
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    rc = review_and_fix.commit_fixes(["--message", "fix review"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "COMMITTED=true" in out
    assert "SHA=deadbeef" in out


@pytest.mark.commit_fixes
def test_commit_fixes_marks_token_and_timing(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    (impl / "session-env.sh").write_text(
        "LARCH_TOKEN_SESSION_ID=parent-session\nLARCH_TIMING_LEDGER=/tmp/ledger.tsv\n",
        encoding="utf-8",
    )
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(argv, **kwargs):
        env = kwargs.get("env", {})
        calls.append((list(argv), dict(env) if env else {}))
        return review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    rc = review_and_fix.commit_fixes(["--message", "fix review"])
    assert rc == 0
    token_calls = [argv for argv, _env in calls if "token" in argv and "mark" in argv]
    timing_calls = [(argv, env) for argv, env in calls if "timing" in argv and "mark" in argv]
    assert token_calls
    assert timing_calls
    assert "Step 7 — commit review fixes" in token_calls[0]
    assert "Step 7 — commit review fixes" in timing_calls[0][0]
    assert timing_calls[0][1].get("LARCH_TIMING_SKILL") == "implement"


@pytest.mark.commit_fixes
def test_commit_fixes_replaces_empty_session_backed_env(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(impl))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "")
    monkeypatch.setenv("LARCH_TIMING_LEDGER", "")
    (impl / "session-env.sh").write_text(
        "LARCH_TOKEN_SESSION_ID=parent-session\nLARCH_TIMING_LEDGER=/tmp/ledger.tsv\n",
        encoding="utf-8",
    )
    calls: list[tuple[list[str], dict[str, str]]] = []

    def fake_run(argv, **kwargs):
        env = kwargs.get("env", {})
        calls.append((list(argv), dict(env) if env else {}))
        return review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    monkeypatch.setattr(review_and_fix, "_git_head", lambda: "deadbeef")
    rc = review_and_fix.commit_fixes(["--message", "fix review"])
    assert rc == 0
    timing_calls = [(argv, env) for argv, env in calls if "timing" in argv and "mark" in argv]
    assert timing_calls
    assert timing_calls[0][1].get("LARCH_TIMING_LEDGER") == "/tmp/ledger.tsv"


@MARK_DISPATCH
def test_apply_findings_rehydrates_session_env_before_coder(tmp_path, monkeypatch):
    monkeypatch.delenv("LARCH_TOKEN_SESSION_ID", raising=False)
    monkeypatch.delenv("LARCH_TIMING_LEDGER", raising=False)
    monkeypatch.setenv("CODEX_BINARY_FOUND", "true")
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    session = tmp_path / "session-env.sh"
    session.write_text(
        "LARCH_TOKEN_SESSION_ID=parent-session\nLARCH_TIMING_LEDGER=/tmp/ledger.tsv\n"
        "CODEX_PRESENT=false\nCURSOR_PRESENT=false\nCODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=false\n",
        encoding="utf-8",
    )
    findings = tmp_path / "findings.md"
    findings.write_text("### FINDING_1: x\n- **Severity**: nit\n", encoding="utf-8")
    seen: dict[str, str] = {}

    def fake_coder(input_file, round_dir, result_file, round_num=None):
        del input_file, round_dir, result_file, round_num
        seen["token"] = os.environ.get("LARCH_TOKEN_SESSION_ID", "")
        seen["ledger"] = os.environ.get("LARCH_TIMING_LEDGER", "")
        seen["codex"] = os.environ.get("CODEX_BINARY_FOUND", "")
        seen["cursor"] = os.environ.get("CURSOR_BINARY_FOUND", "")
        return review_and_fix.CoderResult(0, status="no-changes")

    monkeypatch.setattr(review_and_fix, "apply_findings_with_coder", fake_coder)
    rc = review_and_fix.apply_findings([
        "--findings-file", str(findings),
        "--review-tmpdir", str(tmp_path / "review"),
        "--session-env-path", str(session),
    ])
    assert rc == 0
    assert seen["token"] == "parent-session"
    assert seen["ledger"] == "/tmp/ledger.tsv"
    assert seen["codex"] == "false"
    assert seen["cursor"] == "false"


@MARK_DISPATCH
def test_apply_findings_uses_flat_review_tmpdir_timing_ledger_without_session_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    monkeypatch.delenv("LARCH_TIMING_LEDGER", raising=False)
    findings = tmp_path / "findings.md"
    findings.write_text("### FINDING_1: apply me\n- Suggested revision: change file.\n", encoding="utf-8")
    review_tmpdir = tmp_path / "review"
    session_env = tmp_path / "session-env.sh"
    session_env.write_text("CODEX_BINARY_FOUND=false\nCURSOR_BINARY_FOUND=true\n", encoding="utf-8")
    seen: dict[str, Path] = {}

    def fake_scrub(input_file: Path, output_file: Path, _log_file: Path) -> tuple[bool, int]:
        shutil.copyfile(input_file, output_file)
        return True, 0

    def fake_cursor(round_dir: Path, _prompt: str, tool_log: Path) -> bool:
        seen["ledger"] = review_and_fix._resolve_coder_timing_ledger(round_dir)
        tool_log.write_text("APPLIED: FINDING_1\n", encoding="utf-8")
        return True

    monkeypatch.setattr(review_and_fix, "_scrub_findings", fake_scrub)
    monkeypatch.setattr(review_and_fix, "_submodule_paths", list)
    monkeypatch.setattr(review_and_fix, "_run_coder_cursor", fake_cursor)
    monkeypatch.setattr(review_and_fix, "_run_coder_codex", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "_git_status_porcelain", lambda: "")

    rc = review_and_fix.apply_findings([
        "--findings-file", str(findings),
        "--review-tmpdir", str(review_tmpdir),
        "--session-env-path", str(session_env),
    ])

    assert rc == 0
    assert seen["ledger"] == review_tmpdir / "timing-ledger.tsv"
    assert "REVIEW_AND_FIX_STATUS=complete" in capsys.readouterr().out


@MARK_DISPATCH
def test_scrub_findings_missing_output_fails_closed(tmp_path, monkeypatch):
    input_file = tmp_path / "in.md"
    output_file = tmp_path / "out.md"
    input_file.write_text("### FINDING_1: x\n", encoding="utf-8")

    def fake_run(_argv, **_kwargs):
        class Result:
            returncode = 0
            stdout = "SCRUB_OK=true\nSCRUB_COUNT=0\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    ok, count = review_and_fix._scrub_findings(input_file, output_file, tmp_path / "scrub.log")
    assert ok is False
    assert count == 0
    assert not output_file.exists()


def test_review_core_capture_rejects_non_executable_override(tmp_path, monkeypatch):
    override = tmp_path / "fake-core.sh"
    override.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_TEST_REVIEW_CORE_OVERRIDE", "1")
    monkeypatch.setenv("REVIEW_AND_FIX_REVIEW_CORE_SH", str(override))
    env_path = tmp_path / "review-core.env"
    rc = review_and_fix.review_core_capture(["--round-num", "1"], env_path, implement_tmpdir=tmp_path)
    assert rc == 2
    assert "override-not-executable" in env_path.read_text(encoding="utf-8")


@MARK_DISPATCH
def test_run_coder_cursor_acquires_external_startup_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("CURSOR_PRESENT", "true")
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    monkeypatch.setattr(review_and_fix, "_cursor_available", lambda: True)
    monkeypatch.setattr(review_and_fix.time, "time", mock.Mock(side_effect=[100, 125]))
    monkeypatch.setattr(
        review_and_fix.agents,
        "cursor_auth_preflight",
        lambda **_kw: review_and_fix.agents.AuthVerdict(ok=True, rc=0),
    )
    monkeypatch.setattr(review_and_fix.agents, "cursor_auth_export_env", lambda: None)
    monkeypatch.setattr(
        review_and_fix.agents,
        "resolve_model_args",
        lambda *_a, **_k: review_and_fix.agents.ModelArgResult(argv=("--model", "test")),
    )
    lock_calls: list[str] = []
    release_calls: list[review_and_fix.agents.StartupLockState] = []
    run_calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_acquire(tool):
        lock_calls.append(tool)
        return review_and_fix.agents.StartupLockState(None)

    def fake_release(state):
        release_calls.append(state)

    monkeypatch.setattr(review_and_fix.agents, "external_startup_lock_acquire", fake_acquire)
    monkeypatch.setattr(review_and_fix.agents, "external_startup_lock_release_after", fake_release)

    def fake_run(argv: list[str], **kwargs: object) -> review_and_fix.proc.CommandResult:
        run_calls.append((argv, kwargs))
        stdout = "wrapped prompt" if "cursor-wrap-prompt" in argv else ""
        return review_and_fix.proc.CommandResult(tuple(argv), 0, stdout, "", 0.0)

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    assert review_and_fix._run_coder_cursor(tmp_path, "prompt", tmp_path / "tool.log") is True
    assert lock_calls == ["cursor"]
    assert len(release_calls) == 1
    timing_calls = [call for call in run_calls if call[0][2:4] == ["timing", "record-vendor-task"]]
    assert len(timing_calls) == 1
    argv = timing_calls[0][0]
    assert argv[argv.index("--ledger") + 1] == str(tmp_path / "timing-ledger.tsv")
    assert argv[argv.index("--task-kind") + 1] == "cursor-review-fix"
    assert argv[argv.index("--output") + 1] == str(tmp_path / "coder-cursor.log")
    assert argv[argv.index("--start-s") + 1] == "100"
    assert argv[argv.index("--end-s") + 1] == "125"


@MARK_CONVERGENCE
def test_important_present_matches_concern_only_marker(tmp_path):
    findings = tmp_path / "findings.md"
    findings.write_text(
        "### FINDING_1: title without heading tag\n- **Concern**: [Important] real issue\n",
        encoding="utf-8",
    )
    assert review_and_fix._important_present(findings) is True


@MARK_CONVERGENCE
def test_run_round_missing_findings_sets_classifier_failed(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: [OUT_OF_SCOPE] real issue\n- **Severity**: important\n", encoding="utf-8")

    def fake_capture(core_args, core_out, **_kwargs):
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        dest = out_dir / "accepted-findings.md"
        if accepted.resolve() != dest.resolve():
            shutil.copyfile(accepted, dest)
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=ok",
                "ACCEPTED_COUNT=1",
                "REJECTED_COUNT=0",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(review_and_fix, "review_core_capture", fake_capture)
    monkeypatch.setattr(review_and_fix, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(review_and_fix, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "1", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.status == "classifier-failed"
    assert result.rc == 2


@MARK_CONVERGENCE
def test_prior_summary_accumulates_exonerated_and_neutral(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    (impl / "review-and-fix-summary.json").write_text(
        json.dumps({
            "schema_version": 3,
            "rounds_completed": 1,
            "accepted_count": 1,
            "rejected_count": 2,
            "exonerated_count": 3,
            "neutral_count": 4,
        }),
        encoding="utf-8",
    )
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("", encoding="utf-8")

    def fake_capture(core_args, core_out, **_kwargs):
        out_dir = Path(core_args[core_args.index("--output-dir") + 1])
        (out_dir / "accepted-findings.md").write_text("", encoding="utf-8")
        core_out.write_text(
            "\n".join([
                "REVIEW_CORE_STATUS=ok",
                "ACCEPTED_COUNT=0",
                "REJECTED_COUNT=0",
                "EXONERATED_COUNT=2",
                "NEUTRAL_COUNT=1",
                f"ACCEPTED_FINDINGS_FILE={out_dir / 'accepted-findings.md'}",
                f"REJECTED_FINDINGS_FILE={out_dir / 'rejected-findings.md'}",
            ]) + "\n",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(review_and_fix, "review_core_capture", fake_capture)
    monkeypatch.setattr(review_and_fix, "_compose_review_findings_output", lambda *_a, **_k: False)
    monkeypatch.setattr(review_and_fix, "flush_review_batches", lambda *_a, **_k: True)
    monkeypatch.setattr(review_and_fix, "flush_round_log_after_coder", lambda *_a, **_k: None)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0))
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl), "--round-num", "2", "--mode", "single",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--run-id", "run-1",
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    result = review_and_fix._run_round(args, suppress_emit=True)
    assert result.total_exonerated_count == 5
    assert result.total_neutral_count == 5
    summary = json.loads((impl / "review-and-fix-summary.json").read_text(encoding="utf-8"))
    assert summary["exonerated_count"] == 5
    assert summary["neutral_count"] == 5


@MARK_STEP5
def test_step5_loop_complete_returns_zero_despite_round_rc(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
        del args, suppress_emit, review_core_impl
        return review_and_fix.RoundResult(
            2, "complete", "ok", 1, 0, 0, 0, 0, 0, 0, 0, 0,
            impl / "round-1" / "accepted-findings.md",
            impl / "round-1" / "rejected-findings.md",
            impl / "round-1",
            impl / "review-and-fix-summary.json",
            impl / "accumulated-oos.jsonl",
            review_and_fix.CoderResult(0),
        )

    monkeypatch.setattr(review_and_fix, "_run_round", fake_round)
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda _argv: 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=complete" in out


@MARK_STEP5
def test_step5_loop_preflight_failure_touches_progress_done(tmp_path, monkeypatch):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "plan.txt").write_text("", encoding="utf-8")
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    assert rc == 2
    assert (impl / "progress" / "done").is_file()


@MARK_CHECK_CHANGES
def _mk_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    review_and_fix._run(["git", "init", "--quiet"], cwd=repo)
    review_and_fix._run(["git", "config", "user.email", "test@example.com"], cwd=repo)
    review_and_fix._run(["git", "config", "user.name", "Test"], cwd=repo)
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "tracked.txt"], cwd=repo)
    review_and_fix._run(["git", "commit", "--quiet", "-m", "initial"], cwd=repo)
    return repo


@MARK_CHECK_CHANGES
def test_check_changes_clean_tree_no_baseline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    repo = _mk_git_repo(tmp_path)
    monkeypatch.chdir(repo)
    rc = review_and_fix.check_changes([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=false" in out
    assert "UNTRACKED_BASELINE=missing" in out


@MARK_CHECK_CHANGES
def test_check_changes_preexisting_untracked_with_baseline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    repo = _mk_git_repo(tmp_path)
    (repo / "stray.txt").write_text("x\n", encoding="utf-8")
    ls = review_and_fix._run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo,
    )
    baseline = tmp_path / "baseline.txt"
    baseline.write_text(ls.stdout, encoding="utf-8")
    monkeypatch.chdir(repo)
    rc = review_and_fix.check_changes(["--baseline", str(baseline)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=false" in out
    assert "UNTRACKED_BASELINE=present" in out


@MARK_CHECK_CHANGES
def test_check_changes_head_baseline_detects_commit_movement(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    repo = _mk_git_repo(tmp_path)
    head_bl = repo / "pre-review-head.txt"
    review_and_fix._run(["git", "rev-parse", "HEAD"], cwd=repo)
    head_bl.write_text(review_and_fix._run(["git", "rev-parse", "HEAD"], cwd=repo).stdout, encoding="utf-8")
    (repo / "tracked.txt").write_text("initial\nreview-fix\n", encoding="utf-8")
    review_and_fix._run(["git", "add", "tracked.txt"], cwd=repo)
    review_and_fix._run(["git", "commit", "--quiet", "-m", "Address code review feedback (round 1)"], cwd=repo)
    monkeypatch.chdir(repo)
    rc = review_and_fix.check_changes(["--head-baseline", str(head_bl)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=true" in out


@MARK_CHECK_CHANGES
def test_check_changes_strict_promotes_probe_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    sandbox = tmp_path / "not-a-git-repo"
    sandbox.mkdir()
    monkeypatch.chdir(sandbox)
    rc = review_and_fix.check_changes(["--strict"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FILES_CHANGED=true" in out
    assert "GIT_PROBE_FAILED=true" in out


@MARK_CONVERGENCE
def test_step5_post_round_gates_lint_fix_attempt_cap(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: a\n", encoding="utf-8")
    result = review_and_fix.RoundResult(
        0, "fix-applied", "fix-required", 1, 1, 0, 0, 0, 1, 0, 0, 0,
        accepted, round_dir / "rejected-findings.md", round_dir,
        impl / "review-and-fix-summary.json", impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, input_count=1, status="applied"),
    )
    monkeypatch.setenv("LARCH_STEP5_LINT_FIX_MAX_ATTEMPTS", "1")
    checks_calls = {"n": 0}

    def fake_checks(_impl):
        checks_calls["n"] += 1
        return {"STATUS": "fail", "REDACTED_LOG_FILE": str(impl / "checks.log")}

    def fake_lint(_impl, _log):
        return {"LINT_FIX_STATUS": "applied"}

    monkeypatch.setattr(review_and_fix, "_run_relevant_checks_captured", fake_checks)
    monkeypatch.setattr(review_and_fix, "_run_lint_fix_loop", fake_lint)
    status, reason, cont = review_and_fix._step5_post_round_gates(result, 1, 5, impl)
    assert status == "stall"
    assert reason == "lint-fix-attempt-cap"
    assert cont is False


@MARK_CONVERGENCE
def test_step5_post_round_gates_bulk_skip_ratio_continues(tmp_path, monkeypatch):
    impl = _tmp_impl(tmp_path)
    round_dir = impl / "round-1"
    round_dir.mkdir(parents=True)
    accepted = round_dir / "accepted-findings.md"
    accepted.write_text("### FINDING_1: a\n", encoding="utf-8")
    result = review_and_fix.RoundResult(
        0, "fix-applied", "fix-required", 1, 4, 0, 0, 0, 4, 0, 0, 0,
        accepted, round_dir / "rejected-findings.md", round_dir,
        impl / "review-and-fix-summary.json", impl / "accumulated-oos.jsonl",
        review_and_fix.CoderResult(0, input_count=4, status="applied"),
        skipped_finding_count=3,
    )
    monkeypatch.setattr(review_and_fix, "_run_relevant_checks_captured", lambda _impl: {"STATUS": "pass", "RELEVANT_CHECKS_OK": "true"})
    monkeypatch.setattr(review_and_fix, "_skip_ratio_threshold", lambda: 0.5)
    status, reason, cont = review_and_fix._step5_post_round_gates(result, 1, 5, impl)
    assert status is None
    assert reason is None
    assert cont is True


@MARK_DISPATCH
def test_core_args_for_round_forwards_pre_scouted_manifest(tmp_path):
    impl = _tmp_impl(tmp_path)
    manifest = impl / "scout-coder-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--round-num", "1",
        "--session-env-path", str(impl / "session-env.sh"),
        "--plan-file", str(impl / "plan.txt"),
        "--feature-file", str(impl / "feature-description.txt"),
        "--pre-scouted-manifest", str(manifest),
        "--codex-available", "false",
        "--cursor-available", "false",
    ])
    core_args = review_and_fix._core_args_for_round(args, impl / "round-1", "0", impl / "ledger.tsv")
    idx = core_args.index("--pre-scouted-manifest")
    assert core_args[idx + 1] == str(manifest)


@MARK_STEP5
def test_step5_preflight_missing_session_env_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "session-env.sh").unlink()
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out


@MARK_DISPATCH
def test_preflight_auto_forwards_eligible_scout_manifest(tmp_path):
    impl = _tmp_impl(tmp_path)
    (impl / "step2-external-scout-eligible.txt").write_text("ok\n", encoding="utf-8")
    (impl / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    manifest = impl / "scout-coder-manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == str(manifest)


@MARK_DISPATCH
def test_preflight_skips_manifest_when_scout_ineligible(tmp_path):
    impl = _tmp_impl(tmp_path)
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "loop",
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == ""


@MARK_DISPATCH
def test_preflight_mav_apply_clears_pre_scouted_manifest(tmp_path):
    impl = _tmp_impl(tmp_path)
    findings = impl / "accepted.md"
    findings.write_text("### FINDING_1: x\n", encoding="utf-8")
    args = review_and_fix._build_step5_parser().parse_args([
        "--implement-tmpdir", str(impl),
        "--mode", "mav-apply",
        "--round-num", "1",
        "--findings-file", str(findings),
        "--pre-scouted-manifest", str(impl / "scout-coder-manifest.json"),
    ])
    _, _ = review_and_fix._preflight_step5(args)
    assert args.pre_scouted_manifest == ""


@MARK_STEP5
def test_step5_preflight_missing_feature_file_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "feature-description.txt").unlink()
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out


@MARK_STEP5
def test_step5_preflight_invalid_codex_present_emits_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)
    (impl / "session-env.sh").write_text("CODEX_PRESENT=maybe\nCURSOR_PRESENT=false\n", encoding="utf-8")
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out


@MARK_STEP5
def test_step5_unresolved_run_id_preflight_stall(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / "session-env.sh").write_text("CODEX_PRESENT=false\nCURSOR_PRESENT=false\n", encoding="utf-8")
    (impl / "plan.txt").write_text("plan\n", encoding="utf-8")
    (impl / "feature-description.txt").write_text("feature\n", encoding="utf-8")
    core_calls: list[int] = []

    def fake_capture(*_args, **_kwargs):
        core_calls.append(1)
        return 0

    monkeypatch.setattr(review_and_fix, "review_core_capture", fake_capture)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "STEP5_REVIEW_STATUS=stall" in out
    assert "STALL_REASON=preflight-failed" in out
    assert not core_calls


@MARK_DISPATCH
def test_flush_scout_manifest_writes_batch(tmp_path, monkeypatch):
    impl = tmp_path / "impl"
    impl.mkdir()
    round_dir = impl / "round-1"
    round_dir.mkdir()
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    review_and_fix.flush_scout_manifest(
        impl,
        "run-1",
        1,
        round_dir,
        {
            "SCOUT_STATUS": "ok",
            "DYNAMIC_SLOTS": "2",
            "SCOUT_MANIFEST": str(round_dir / "scout-round1-manifest.json"),
            "YIELD_TSV_FILE": str(round_dir / "scout-archetype-yield.tsv"),
        },
    )
    assert calls
    assert "review-scout-manifest" in calls[0]
    payload_path = round_dir / ".scout-payload.json"
    assert not payload_path.exists()


@MARK_DISPATCH
def test_run_coder_cursor_normalizes_api_key_before_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("CURSOR_PRESENT", "true")
    monkeypatch.setenv("CURSOR_BINARY_FOUND", "true")
    monkeypatch.setenv("CURSOR_API_KEY", "  key-with-padding  ")
    monkeypatch.setattr(review_and_fix, "_cursor_available", lambda: True)
    monkeypatch.setattr(
        review_and_fix.agents,
        "resolve_model_args",
        lambda *_a, **_k: review_and_fix.agents.ModelArgResult(argv=("--model", "test")),
    )
    seen_env: list[str | None] = []
    original_export = review_and_fix.agents.cursor_auth_export_env

    def capture_export() -> None:
        original_export()
        seen_env.append(os.environ.get("CURSOR_API_KEY"))

    monkeypatch.setattr(review_and_fix.agents, "cursor_auth_export_env", capture_export)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **_kw: review_and_fix.proc.CommandResult(
        argv, 0, "wrapped prompt", "", 0.0,
    ))
    assert review_and_fix._run_coder_cursor(tmp_path, "prompt", tmp_path / "tool.log") is True
    assert seen_env == ["key-with-padding"]


@MARK_STEP5
def test_step5_checks_wiring_passes_repo_site_and_binary_presence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    impl = _tmp_impl(tmp_path)
    (impl / "session-env.sh").write_text(
        "RUN_ID=run-1\nCODEX_PRESENT=false\nCURSOR_PRESENT=true\nCODEX_BINARY_FOUND=true\nCURSOR_BINARY_FOUND=false\n",
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    monkeypatch.delenv("CODEX_BINARY_FOUND", raising=False)
    monkeypatch.delenv("CURSOR_BINARY_FOUND", raising=False)
    captured_checks: dict[str, object] = {}
    captured_fix: dict[str, object] = {}

    def fake_run_relevant_checks(
        _runner: object,
        *,
        site: str,
        tmpdir: str,
        repo_root: str,
    ) -> checks.ChecksResult:
        captured_checks.update(site=site, tmpdir=tmpdir, repo_root=repo_root)
        return checks.ChecksResult(
            ok=True,
            exit_code=0,
            site=site,
            redacted_log_path=None,
            phase="pre-commit",
            coverage="changed-file-only",
            skipped=False,
            warn=None,
        )

    def fake_run_lint_fix(
        _runner: object,
        *,
        site: str,
        checks_log: str,
        repo_root: str,
        codex_present: bool,
        cursor_present: bool,
        run_parent: str,
        allowed_tmpdir: str | None,
    ) -> checks.FixOutcome:
        captured_fix.update(
            site=site,
            checks_log=checks_log,
            repo_root=repo_root,
            codex_present=codex_present,
            cursor_present=cursor_present,
            run_parent=run_parent,
            allowed_tmpdir=allowed_tmpdir,
        )
        return checks.FixOutcome(
            status="no-changes",
            delta_paths=(),
            failure_reason=None,
            commit_sha=None,
            head_changed=False,
            coder_tool=None,
        )

    monkeypatch.setattr(checks, "run_relevant_checks", fake_run_relevant_checks)
    monkeypatch.setattr(checks, "run_lint_fix", fake_run_lint_fix)
    review_and_fix._run_relevant_checks_captured(impl)
    review_and_fix._run_lint_fix_loop(impl, str(impl / "checks.log"))
    assert captured_checks == {
        "site": "step5-review-fixes",
        "tmpdir": str(impl),
        "repo_root": str(repo),
    }
    assert captured_fix["site"] == "step5"
    assert captured_fix["repo_root"] == str(repo)
    assert captured_fix["codex_present"] is True
    assert captured_fix["cursor_present"] is False
    assert captured_fix["allowed_tmpdir"] == str(impl)
