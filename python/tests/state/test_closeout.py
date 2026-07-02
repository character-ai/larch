"""Tests for closeout.py Step 16/17 helpers."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from larch.state import closeout


def _completed(argv: list[str], rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, rc, stdout="", stderr="")


def _install_closeout_stub(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    step16_fail: bool = False,
    slack_status: str = "skipped",
    step17_mode: str = "success",
    summary_body: str = "# Summary\n",
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    monkeypatch.setenv("STEP16_FAIL", "true" if step16_fail else "false")
    monkeypatch.setenv("SLACK_STATUS", slack_status)
    monkeypatch.setenv("STEP17_MODE", step17_mode)
    monkeypatch.setenv("SUMMARY_BODY", summary_body)

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "review-and-fix" in argv and "write-rejected" in argv:
            if os.environ.get("STEP16_FAIL") == "true":
                if hasattr(stdout, "write"):
                    stdout.write("STATUS=failed\n")  # type: ignore[attr-defined]
                return _completed(argv, 9)
            return _completed(argv)
        if "slack" in argv and "issue-announce" in argv:
            status = os.environ.get("SLACK_STATUS", "skipped")
            if hasattr(stdout, "write"):
                stdout.write(f"STATUS={status}\n")  # type: ignore[attr-defined]
            return _completed(argv)
        if "final-report" in argv and "write" in argv:
            summary = tmp_path / "summary-final.md"
            mode = os.environ.get("STEP17_MODE", "success")
            body = os.environ.get("SUMMARY_BODY", "# Summary\n")
            if mode == "success":
                summary.write_text(body, encoding="utf-8")
                if hasattr(stdout, "write"):
                    stdout.write("STATUS=ok\n")  # type: ignore[attr-defined]
                return _completed(argv)
            if mode == "fail-upsert":
                summary.write_text(body, encoding="utf-8")
                if hasattr(stdout, "write"):
                    stdout.write("tracking upsert failed\n")  # type: ignore[attr-defined]
                return _completed(argv, 7)
            if mode == "fail-empty":
                summary.write_text("", encoding="utf-8")
                if hasattr(stdout, "write"):
                    stdout.write("render failed before body\n")  # type: ignore[attr-defined]
                return _completed(argv, 7)
            if mode == "fail-stale":
                if hasattr(stdout, "write"):
                    stdout.write("render failed before body\n")  # type: ignore[attr-defined]
                return _completed(argv, 7)
            return _completed(argv, 7)
        if "append-failure" in argv:
            log = Path(argv[argv.index("--log") + 1])
            output_file = Path(argv[argv.index("--output-file") + 1])
            category = argv[argv.index("--category") + 1]
            site = argv[argv.index("--site") + 1]
            exit_code = argv[argv.index("--exit-code") + 1]
            redacted = "--redact" in argv
            body = output_file.read_text(encoding="utf-8") if output_file.is_file() else ""
            with log.open("a", encoding="utf-8") as handle:
                handle.write(f"CATEGORY={category}\nSITE={site}\nEXIT={exit_code}\nREDACT={redacted}\n{body}\n")
            return _completed(argv)
        return _completed(argv)

    monkeypatch.setattr(closeout.subprocess, "run", fake_run)


def test_step_16_17_emits_markers_and_step17_printed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path)
    rc = closeout.step_16_17_main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN in out
    assert "# Summary" in out
    assert closeout.SUMMARY_END in out
    assert (tmp_path / ".step17-printed").is_file()
    assert not (tmp_path / ".step17-emitted").exists()


def test_step_16_17_attempts_architectural_guidelines_pin_before_step16(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    calls: list[str] = []

    def fake_pin(**_kwargs: object) -> str:
        calls.append("pin")
        return "ok"

    def fake_step16(_argv: list[str]) -> int:
        calls.append("step16")
        return 0

    def fake_step17(_argv: list[str]) -> int:
        calls.append("step17")
        (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
        return 0

    def fake_slack(**_kwargs: Any) -> None:
        calls.append("slack")

    monkeypatch.setattr(closeout, "_pin_architectural_guidelines_note_best_effort", fake_pin)
    monkeypatch.setattr(closeout, "step_16", fake_step16)
    monkeypatch.setattr(closeout, "_step_16a_slack", fake_slack)
    monkeypatch.setattr(closeout, "step_17", fake_step17)

    assert closeout.step_16_17_main([]) == 0

    captured = capsys.readouterr()
    assert "ARCHITECTURAL_GUIDELINES_PIN_STATUS=ok" in captured.err
    assert calls == ["pin", "step16", "slack", "step17"]
    assert closeout.SUMMARY_BEGIN in captured.out


def test_step_16_17_pin_exception_does_not_block_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path)

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, "abc123\n", "")
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, str(Path.cwd()) + "\n", "")
        stdout = kwargs.get("stdout")
        if "final-report" in argv and "write" in argv:
            (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
            if hasattr(stdout, "write"):
                stdout.write("STATUS=ok\n")  # type: ignore[attr-defined]
        return _completed(argv)

    def raising_pin(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("pin failed")

    monkeypatch.setattr(closeout.architectural_guidelines, "pin_note_from_staged", raising_pin)
    monkeypatch.setattr(closeout.subprocess, "run", fake_run)

    assert closeout.step_16_17_main([]) == 0

    captured = capsys.readouterr()
    assert "ARCHITECTURAL_GUIDELINES_PIN_STATUS=failed" in captured.err
    assert closeout.SUMMARY_BEGIN in captured.out


def test_architectural_guidelines_pin_helper_reports_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, "abc123\n", "")
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, str(Path.cwd()) + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(closeout, "_run", fake_run)

    def no_pin(*_args: object, **_kwargs: object) -> bool:
        return False

    monkeypatch.setattr(closeout.architectural_guidelines, "pin_note_from_staged", no_pin)

    assert closeout._pin_architectural_guidelines_note_best_effort(tmpdir=tmp_path, env={}) == "skipped"


def test_architectural_guidelines_pin_helper_refreshes_staged_assessment_on_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    staged_diff = "stale staged diff"
    live_diff = "current live diff"
    closeout.architectural_guidelines.write_staged_assessment(
        implement_tmpdir=tmp_path,
        assessment_text="note\n",
        assessed_head_sha="old-head",
        diff_fingerprint_value=closeout.architectural_guidelines.diff_fingerprint(staged_diff),
        base_ref="origin/main",
        diff_text=staged_diff,
    )

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, "current-head\n", "")
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, f"{repo}\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def fake_materialize(*_args: object, **_kwargs: object) -> str:
        return live_diff

    monkeypatch.setattr(closeout, "_run", fake_run)
    monkeypatch.setattr(closeout.architectural_guidelines, "materialize_implementation_diff", fake_materialize)

    assert closeout._pin_architectural_guidelines_note_best_effort(tmpdir=tmp_path, env={}) == "ok"
    assert closeout.architectural_guidelines.note_consumable(implement_tmpdir=tmp_path, head_sha="current-head")
    sidecar = (tmp_path / closeout.architectural_guidelines.STAGED_ASSESSMENT_ENV).read_text(encoding="utf-8")
    assert f"DIFF_FINGERPRINT={closeout.architectural_guidelines.diff_fingerprint(live_diff)}" in sidecar
    assert "ASSESSED_HEAD_SHA=current-head" in sidecar


def test_architectural_guidelines_pin_helper_skips_post_merge_mismatched_durable_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closeout.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="note\n",
        head_sha="feature-head",
        metadata={
            "ASSESSED_HEAD_SHA": "old",
            "DIFF_FINGERPRINT": closeout.architectural_guidelines.diff_fingerprint("diff"),
        },
        base_ref="origin/main",
    )
    (tmp_path / "post-merge-sentinel").write_text("MERGE_RESULT=merged\n", encoding="utf-8")

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, "main-head\n", "")
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, str(Path.cwd()) + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    pin_calls: list[str] = []

    def record_pin(_tmpdir: Path, *, head_sha: str, base_ref: str, repo_root: str) -> bool:
        del base_ref, repo_root
        pin_calls.append(head_sha)
        return True

    monkeypatch.setattr(closeout, "_run", fake_run)
    monkeypatch.setattr(closeout.architectural_guidelines, "pin_note_from_staged", record_pin)

    assert closeout._pin_architectural_guidelines_note_best_effort(tmpdir=tmp_path, env={}) == "skipped"
    assert not pin_calls


def test_architectural_guidelines_pin_helper_calls_pin_without_post_merge_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closeout.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="note\n",
        head_sha="feature-head",
        metadata={
            "ASSESSED_HEAD_SHA": "old",
            "DIFF_FINGERPRINT": closeout.architectural_guidelines.diff_fingerprint("diff"),
        },
        base_ref="origin/main",
    )

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, "main-head\n", "")
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, str(Path.cwd()) + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    pin_calls: list[str] = []

    def record_pin(_tmpdir: Path, *, head_sha: str, base_ref: str, repo_root: str) -> bool:
        del base_ref, repo_root
        pin_calls.append(head_sha)
        return True

    monkeypatch.setattr(closeout, "_run", fake_run)
    monkeypatch.setattr(closeout.architectural_guidelines, "pin_note_from_staged", record_pin)

    assert closeout._pin_architectural_guidelines_note_best_effort(tmpdir=tmp_path, env={}) == "ok"
    assert pin_calls == ["main-head"]


def test_architectural_guidelines_pin_helper_calls_pin_when_post_merge_head_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closeout.architectural_guidelines.write_implement_note(
        implement_tmpdir=tmp_path,
        note_text="note\n",
        head_sha="main-head",
        metadata={
            "ASSESSED_HEAD_SHA": "old",
            "DIFF_FINGERPRINT": closeout.architectural_guidelines.diff_fingerprint("diff"),
        },
        base_ref="origin/main",
    )
    (tmp_path / "post-merge-sentinel").write_text("MERGE_RESULT=merged\n", encoding="utf-8")

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, "main-head\n", "")
        if argv[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(argv, 0, str(Path.cwd()) + "\n", "")
        return subprocess.CompletedProcess(argv, 0, "", "")

    pin_calls: list[str] = []

    def record_pin(_tmpdir: Path, *, head_sha: str, base_ref: str, repo_root: str) -> bool:
        del base_ref, repo_root
        pin_calls.append(head_sha)
        return True

    monkeypatch.setattr(closeout, "_run", fake_run)
    monkeypatch.setattr(closeout.architectural_guidelines, "pin_note_from_staged", record_pin)

    assert closeout._pin_architectural_guidelines_note_best_effort(tmpdir=tmp_path, env={}) == "ok"
    assert pin_calls == ["main-head"]


def test_step_16_17_requires_tmpdir(capsys: pytest.CaptureFixture[str]) -> None:
    rc = closeout.step_16_17_main([])
    assert rc == 2
    assert "IMPLEMENT_TMPDIR required" in capsys.readouterr().err


def test_step17_no_print_restores_stale_summary_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step17_mode="fail-stale")
    (tmp_path / "summary-final.md").write_text("old\n", encoding="utf-8")
    rc = closeout.step_17_main(["--no-print-stdout"])
    assert rc == 7
    assert (tmp_path / "summary-final.md").read_text(encoding="utf-8") == "old\n"


def test_step_16_17_slack_skipped_no_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, slack_status="skipped")
    assert closeout.step_16_17_main([]) == 0
    assert not (tmp_path / "execution-issues.md").exists()


def test_step16_17_records_failed_slack_as_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, slack_status="failed")
    assert closeout.step_16_17_main([]) == 0
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "CATEGORY=Warnings" in issues


def test_step_16_17_step16_failure_still_emits_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step16_fail=True)
    assert closeout.step_16_17_main([]) == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN in out


def test_step_16_17_stale_failure_prints_no_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step17_mode="fail-stale")
    (tmp_path / "summary-final.md").write_text("stale body\n", encoding="utf-8")
    assert closeout.step_16_17_main([]) == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN not in out
    assert not (tmp_path / ".step17-printed").exists()
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "CATEGORY=Tool Failures" in issues
    assert (tmp_path / "summary-final.md").read_text(encoding="utf-8") == "stale body\n"


def test_step17_no_print_returns_zero_when_fresh_summary_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step17_mode="fail-upsert", summary_body="fresh body\n")
    rc = closeout.step_17_main(["--no-print-stdout"])
    assert rc == 0
    assert (tmp_path / "summary-final.md").read_text(encoding="utf-8") == "fresh body\n"


def test_step_16_17_upsert_failure_without_prior_summary_emits_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step17_mode="fail-upsert", summary_body="fresh body\n")
    assert closeout.step_16_17_main([]) == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN in out
    assert "fresh body" in out
    assert (tmp_path / ".step17-printed").is_file()
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "CATEGORY=Tool Failures" in issues


def test_step_16_17_upsert_failure_emits_markers_after_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step17_mode="fail-upsert", summary_body="fresh body\n")
    (tmp_path / "summary-final.md").write_text("old body\n", encoding="utf-8")
    assert closeout.step_16_17_main([]) == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN in out
    assert "fresh body" in out
    assert (tmp_path / ".step17-printed").is_file()
    issues = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "CATEGORY=Tool Failures" in issues


def test_step_16_17_empty_failure_prints_no_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_closeout_stub(monkeypatch, tmp_path, step17_mode="fail-empty")
    assert closeout.step_16_17_main([]) == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN not in out
    assert not (tmp_path / ".step17-printed").exists()


def test_read_key_returns_cli_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    session = tmp_path / "session-env.sh"
    session.write_text("LARCH_RUN_ID=session-run\n", encoding="utf-8")
    assert closeout._read_key(path=session, key="LARCH_RUN_ID", default="") == "session-run"


@pytest.mark.parametrize(
    ("session_text", "ship_text", "finalize_text", "expected_run_id"),
    [
        ("LARCH_RUN_ID=session-run\n", "RUN_ID=ship-run\n", "RUN_ID=finalize-run\n", "session-run"),
        ("", "RUN_ID=ship-run\n", "RUN_ID=finalize-run\n", "ship-run"),
        ("", "", "RUN_ID=finalize-run\n", "finalize-run"),
    ],
)
def test_step_16_forwards_run_id_from_state_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    session_text: str,
    ship_text: str,
    finalize_text: str,
    expected_run_id: str,
) -> None:
    plugin_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    (tmp_path / "session-env.sh").write_text(session_text, encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").write_text(ship_text, encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text(finalize_text, encoding="utf-8")

    captured: list[str] = []
    real_run = subprocess.run

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "write-rejected" in argv:
            captured.append(argv[argv.index("--run-id") + 1])
            return _completed(argv)
        if "telemetry-mark" in argv:
            return _completed(argv)
        if "session" in argv and "read-key" in argv:
            return real_run(
                argv,
                text=True,
                env=kwargs.get("env"),
                stdout=kwargs.get("stdout", subprocess.PIPE),
                stderr=kwargs.get("stderr", subprocess.DEVNULL),
                check=False,
            )
        return _completed(argv)

    monkeypatch.setattr(closeout.subprocess, "run", fake_run)
    assert closeout.step_16_main([]) == 0
    assert captured == [expected_run_id]
