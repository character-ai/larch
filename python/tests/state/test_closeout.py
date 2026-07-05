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


def _read_key_completed(argv: list[str]) -> subprocess.CompletedProcess[str] | None:
    if "session" not in argv or "read-key" not in argv:
        return None
    path = Path(argv[argv.index("--file") + 1])
    key = argv[argv.index("--key") + 1]
    default = argv[argv.index("--default") + 1]
    value = default
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1]
    return subprocess.CompletedProcess(argv, 0, value + "\n", "")


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


def test_step_16_17_runs_step16_without_guidelines_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    calls: list[str] = []

    def fake_step16(_argv: list[str]) -> int:
        calls.append("step16")
        return 0

    def fake_step17(_argv: list[str]) -> int:
        calls.append("step17")
        (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
        return 0

    def fake_slack(**_kwargs: Any) -> None:
        calls.append("slack")

    monkeypatch.setattr(closeout, "step_16", fake_step16)
    monkeypatch.setattr(closeout, "_step_16a_slack", fake_slack)
    monkeypatch.setattr(closeout, "step_17", fake_step17)

    assert closeout.step_16_17_main([]) == 0

    captured = capsys.readouterr()
    assert "ARCHITECTURAL_GUIDELINES_PIN_STATUS" not in captured.err
    assert calls == ["step16", "slack", "step17"]
    assert closeout.SUMMARY_BEGIN in captured.out


def test_step_16_16a_runs_without_guidelines_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))
    calls: list[str] = []

    def fake_step16(_argv: list[str]) -> int:
        calls.append("step16")
        return 0

    def fake_slack(**_kwargs: Any) -> None:
        calls.append("slack")

    monkeypatch.setattr(closeout, "step_16", fake_step16)
    monkeypatch.setattr(closeout, "_step_16a_slack", fake_slack)

    assert closeout.step_16_16a_main([]) == 0

    captured = capsys.readouterr()
    assert "ARCHITECTURAL_GUIDELINES_PIN_STATUS" not in captured.err
    assert calls == ["step16", "slack"]


def test_step_16_17_does_not_create_guidelines_pin_sentinel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parents[3]))

    def fake_step16(_argv: list[str]) -> int:
        return 0

    def fake_step17(_argv: list[str]) -> int:
        (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
        return 0

    def fake_slack(**_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(closeout, "step_16", fake_step16)
    monkeypatch.setattr(closeout, "_step_16a_slack", fake_slack)
    monkeypatch.setattr(closeout, "step_17", fake_step17)

    assert closeout.step_16_16a_main([]) == 0
    assert closeout.step_16_17_main([]) == 0

    captured = capsys.readouterr()
    assert "ARCHITECTURAL_GUIDELINES_PIN_STATUS" not in captured.err
    assert not (tmp_path / ".architectural-guidelines-pin-done").exists()


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
# pyright: reportUnusedFunction=false
