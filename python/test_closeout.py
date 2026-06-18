"""Tests for closeout.py Step 16/17 helpers."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

import closeout


def _completed(argv: list[str], rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, rc, stdout="", stderr="")


def test_step_16_17_emits_markers_and_step17_printed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "final-report" in argv and "write" in argv:
            (tmp_path / "summary-final.md").write_text("# Summary\n", encoding="utf-8")
            if hasattr(stdout, "write"):
                stdout.write("STATUS=ok\n")  # type: ignore[attr-defined]
        elif "slack" in argv and hasattr(stdout, "write"):
            stdout.write("STATUS=skipped\n")  # type: ignore[attr-defined]
        return _completed(argv)

    monkeypatch.setattr(closeout.subprocess, "run", fake_run)
    rc = closeout.step_16_17_main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert closeout.SUMMARY_BEGIN in out
    assert "# Summary" in out
    assert closeout.SUMMARY_END in out
    assert (tmp_path / ".step17-printed").is_file()
    assert not (tmp_path / ".step17-emitted").exists()


def test_step17_no_print_restores_stale_summary_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))
    (tmp_path / "summary-final.md").write_text("old\n", encoding="utf-8")

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        stdout = kwargs.get("stdout")
        if "final-report" in argv and "write" in argv:
            if hasattr(stdout, "write"):
                stdout.write("ERROR=boom\n")  # type: ignore[attr-defined]
            return _completed(argv, 3)
        return _completed(argv)

    monkeypatch.setattr(closeout.subprocess, "run", fake_run)
    rc = closeout.step_17_main(["--no-print-stdout"])
    assert rc == 3
    assert (tmp_path / "summary-final.md").read_text(encoding="utf-8") == "old\n"


def test_step16_17_records_failed_slack_as_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(Path.cwd()))
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        stdout = kwargs.get("stdout")
        if "slack" in argv and hasattr(stdout, "write"):
            stdout.write("STATUS=failed\n")  # type: ignore[attr-defined]
        if "final-report" in argv and "write" in argv:
            (tmp_path / "summary-final.md").write_text("summary\n", encoding="utf-8")
        return _completed(argv)

    monkeypatch.setattr(closeout.subprocess, "run", fake_run)
    assert closeout.step_16_17_main([]) == 0
    assert any("append-failure" in call for call in calls)
