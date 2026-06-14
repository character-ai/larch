from pathlib import Path
from unittest.mock import patch

import pytest

import step_7a


def test_step7a_emits_terminal_kvs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    def fake_generate_code_flow_diagram(implement_tmpdir: Path, *, base_remote: str, base_ref: str) -> tuple[int, str, str, str]:
        _ = (base_remote, base_ref)
        diagram = implement_tmpdir / "code-flow-diagram.md"
        _ = diagram.write_text("## Code Flow Diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n", encoding="utf-8")
        return 0, "ok", str(diagram), ""

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=False), patch.object(
        step_7a.pr_body,
        "generate_code_flow_diagram",
        side_effect=fake_generate_code_flow_diagram,
    ), patch.object(
        step_7a.run_logs,
        "flush_logs_pre",
    ) as mock_flush, patch.object(
        step_7a,
        "subprocess",
    ) as mock_subprocess:
        mock_flush.return_value.skipped = True
        mock_flush.return_value.reason = "no-repo-cwd"
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=" in out
    assert "LOG_FLUSH_STATUS=" in out
    assert (tmp_path / "code-flow-diagram.md").is_file()


def test_step7a_main_rejects_unknown_flags(capsys: pytest.CaptureFixture[str]) -> None:
    rc = step_7a.main(["--implement-tmpdir", "/tmp/x", "--unknown-flag", "1"])

    assert rc == 2
    out = capsys.readouterr().out
    assert "STEP_7A_BAIL_REASON=argv" in out


def test_step7a_skips_diagram_for_small_non_runtime_change(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    def fake_is_small_non_runtime_change(*, base_remote: str, base_ref: str) -> bool:
        _ = (base_remote, base_ref)
        return True

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", fake_is_small_non_runtime_change)
    with patch.object(step_7a, "_run_log_flush", return_value="skip"), patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=skip" in out
    assert "reason=small-non-runtime-change" in out


def test_step7a_honors_issue_number_and_run_id(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-env.sh").write_text(
        "LARCH_ISSUE_NUMBER=99\nLARCH_RUN_ID=run-99\n",
        encoding="utf-8",
    )

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_log_flush",
        return_value="skip",
    ), patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path, issue_number="42", run_id="run-42")

    assert rc == 0
    assert "reason=small-non-runtime-change" in capsys.readouterr().out
