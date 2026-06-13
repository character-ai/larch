# pyright: reportUnusedCallResult=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import os
from pathlib import Path

import logging_util
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


def test_apply_findings_empty_file_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    findings = tmp_path / "findings.md"
    findings.write_text("", encoding="utf-8")
    rc = review_and_fix.apply_findings(["--findings-file", str(findings), "--review-tmpdir", str(tmp_path / "review")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "REVIEW_AND_FIX_STATUS=no-findings" in out
    assert "CODER_STATUS=skipped" in out


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
