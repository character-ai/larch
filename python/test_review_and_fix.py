# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# ruff: noqa: ARG001, ARG005
from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import logging_util
import pytest
import review_and_fix


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


@pytest.mark.parsers
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


@pytest.mark.loop_timing
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


@pytest.mark.dispatch
def test_apply_findings_empty_file_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    findings = tmp_path / "findings.md"
    findings.write_text("", encoding="utf-8")
    rc = review_and_fix.apply_findings(["--findings-file", str(findings), "--review-tmpdir", str(tmp_path / "review")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEW_AND_FIX_STATUS=no-findings" in out
    assert "CODER_STATUS=skipped" in out


@pytest.mark.check_changes
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


@pytest.mark.write_rejected
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


@pytest.mark.dispatch
def test_compose_coder_prompt_uses_canonical_submodule_prohibition(tmp_path):
    submodules = ["vendor/foo"]
    body = review_and_fix._compose_coder_prompt(tmp_path / "prompt.md", tmp_path / "f.md", tmp_path, submodules)
    assert "Do NOT read, edit, create, delete, move" in body
    assert "Do NOT touch `.git/`" in body


@pytest.mark.dispatch
def test_run_coder_codex_rejects_nonzero_launcher_exit(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_PRESENT", "true")
    monkeypatch.setattr(review_and_fix, "_codex_available", lambda: True)
    output = tmp_path / "coder-codex.log"
    output.write_text("ok\n", encoding="utf-8")

    def fake_run(argv, **kwargs):
        class Result:
            returncode = 0
            stdout = "LAUNCHER_EXIT=1\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(review_and_fix, "_run", fake_run)
    assert review_and_fix._run_coder_codex(tmp_path, "prompt", tmp_path / "tool.log") is False


@pytest.mark.dispatch
def test_dynamic_archetypes_defaults_to_zero_without_config(monkeypatch, tmp_path):
    monkeypatch.delenv("LARCH_DYNAMIC_ARCHETYPES_MAX", raising=False)
    args = mock.Mock(dynamic_archetypes="", session_env_path="")
    assert review_and_fix._dynamic_archetypes(args, tmp_path) == "0"


@pytest.mark.dispatch
def test_post_dispatch_submodule_revert_restores_tracked_path(tmp_path, monkeypatch):
    sub = tmp_path / "vendor"
    sub.mkdir()
    (sub / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    round_dir = tmp_path / "round-1"
    round_dir.mkdir()
    monkeypatch.setattr(review_and_fix, "_capture_round_tracked_paths", lambda: ["vendor/tracked.txt"])
    monkeypatch.setattr(review_and_fix, "_capture_round_untracked_paths", list)
    monkeypatch.setattr(review_and_fix, "_run", lambda argv, **kw: review_and_fix.proc.CommandResult(argv, 0, "", "", 0.0))
    count = review_and_fix._post_dispatch_submodule_revert(round_dir, ["vendor"])
    assert count == 1


@pytest.mark.step5
def test_step5_handoff_envelope_uses_false_stall_tracking(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    impl = _tmp_impl(tmp_path)

    def fake_round(args, *, suppress_emit, review_core_impl=None):
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
    monkeypatch.setattr(review_and_fix, "record_round_timing", lambda argv: 0)
    rc = review_and_fix.step5(["--implement-tmpdir", str(impl), "--mode", "loop", "--starting-round", "1", "--round-cap", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "STEP5_REVIEW_STATUS=coder-main-agent-required" in out
    assert "STALL_TRACKING=false" in out


@pytest.mark.starting_round
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


@pytest.mark.starting_round
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


@pytest.mark.step5
def test_mav_apply_writes_relocated_pre_coder_head(tmp_path, monkeypatch, capsys):
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
    assert not (impl / "round-1" / "pre-coder-head.txt").exists()


@pytest.mark.write_rejected
def test_write_rejected_redacts_tmpdir_and_secrets(tmp_path, monkeypatch, capsys):
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


@pytest.mark.parsers
def test_step5_parse_checks_capture_requires_status_or_ok_fields():
    parsed = review_and_fix._parse_checks_capture("RELEVANT_CHECKS_OK=true\n")
    assert parsed["RELEVANT_CHECKS_OK"] == "true"


@pytest.mark.convergence
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


@pytest.mark.dispatch
def test_process_skipped_findings_routes_security_vs_oos(tmp_path, monkeypatch):
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
