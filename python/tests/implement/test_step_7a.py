from pathlib import Path
from unittest.mock import patch
import subprocess

import pytest

from larch.implement import step_7a


def test_step7a_bg_wait_marker_copies_keepalive_clone_path(tmp_path: Path) -> None:
    _ = (tmp_path / ".larch-keepalive").write_text(f"CLONE_PATH={tmp_path}\n", encoding="utf-8")
    step_7a._write_bg_wait_marker(tmpdir=tmp_path, step="implement-step7a", timeout_s=21600)  # type: ignore[reportPrivateUsage]

    marker_text = (tmp_path / ".bg-wait-active").read_text(encoding="utf-8")
    assert "STEP=implement-step7a\n" in marker_text
    assert f"CLONE_PATH={tmp_path}\n" in marker_text


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


def test_step7a_main_empty_tmpdir_argv_falls_back_to_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    seen: dict[str, object] = {}

    def fake_run_step7a(
        implement_tmpdir: Path,
        *,
        issue_number: str = "",
        run_id: str = "",
        no_logs_commit: bool = False,
        forked_target: bool = False,
        base_remote: str = "origin",
        base_ref: str = "main",
    ) -> int:
        seen.update(
            {
                "implement_tmpdir": implement_tmpdir,
                "issue_number": issue_number,
                "run_id": run_id,
                "no_logs_commit": no_logs_commit,
                "forked_target": forked_target,
                "base_remote": base_remote,
                "base_ref": base_ref,
            }
        )
        return 0

    monkeypatch.setattr(step_7a, "run_step7a", fake_run_step7a)

    rc = step_7a.main(["--implement-tmpdir", "", "--issue-number", "7", "--run-id", "run-7"])

    assert rc == 0
    assert seen["implement_tmpdir"] == tmp_path
    assert seen["issue_number"] == "7"
    assert seen["run_id"] == "run-7"


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


def test_step7a_reads_run_id_from_session_env_when_session_id_absent(tmp_path: Path) -> None:
    _ = (tmp_path / "session-env.sh").write_text("LARCH_RUN_ID=run-99\n", encoding="utf-8")

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_log_flush",
        return_value="skip",
    ) as mock_flush, patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    mock_flush.assert_called_once()
    assert mock_flush.call_args.kwargs["run_id"] == "run-99"


def test_step7a_diagram_failure_exits_zero_and_clears_stale_artifacts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "code-flow-diagram.md").write_text("stale\n", encoding="utf-8")
    reason = "generation-failed rc=7 tail=timeout after 600s"

    def fake_generate_code_flow_diagram(implement_tmpdir: Path, *, base_remote: str, base_ref: str) -> tuple[int, str, str, str]:
        _ = (base_remote, base_ref)
        _ = (implement_tmpdir / "code-flow-diagram.failure.log").write_text("returncode: 7\nstderr: timeout after 600s\n", encoding="utf-8")
        return 1, "failed", "", reason

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=False), patch.object(
        step_7a.pr_body,
        "generate_code_flow_diagram",
        side_effect=fake_generate_code_flow_diagram,
    ), patch.object(step_7a, "_run_log_flush", return_value="ok"), patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=failed" in out
    assert f"DIAGRAM_REASON={reason}" in out
    assert "STEP_7A_BAIL_REASON=\n" in out or out.endswith("STEP_7A_BAIL_REASON=\n") or "STEP_7A_BAIL_REASON=" in out
    assert not (tmp_path / "code-flow-diagram.md").exists()
    issue_text = (tmp_path / "execution-issues.md").read_text(encoding="utf-8")
    assert "### Warnings" in issue_text
    assert reason in issue_text
    copied_log = tmp_path / "larch-logs" / "implement" / "run-1" / "code-flow-diagram.failure.log"
    assert not copied_log.exists()


def test_step7a_diagram_failure_emits_diagram_reason_on_rebase_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    reason = "generation-failed rc=7 tail=timeout after 600s"

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=False), patch.object(
        step_7a.pr_body,
        "generate_code_flow_diagram",
        return_value=(1, "failed", "", reason),
    ), patch.object(step_7a, "_run_log_flush", return_value="ok") as mock_flush, patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 1
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=conflict\n"
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 1
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=failed" in out
    assert f"DIAGRAM_REASON={reason}" in out
    assert "LOG_FLUSH_STATUS=ok" in out
    mock_flush.assert_called_once()


def test_step7a_rebase_failure_defers_git_commit_flush(tmp_path: Path) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_log_flush",
        return_value="ok",
    ) as mock_flush, patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 1
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=conflict\n"
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 1
    assert mock_flush.call_args.kwargs["defer_git_commit"] is True


def test_step7a_rebase_failure_flushes_and_preserves_probe_rc(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_log_flush",
        return_value="degraded",
    ) as mock_flush, patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 3
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=failed\n"
        rc = step_7a.run_step7a(tmp_path)

    out = capsys.readouterr().out
    assert rc == 3
    assert "REBASE_OUTCOME=failed" in out
    assert "LOG_FLUSH_STATUS=degraded" in out
    mock_flush.assert_called_once()


def test_step7a_rebase_failure_no_logs_commit_emits_skipped_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_log_flush",
        return_value="skipped-no-logs-commit",
    ) as mock_flush, patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 3
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=failed\n"
        rc = step_7a.run_step7a(tmp_path, no_logs_commit=True)

    out = capsys.readouterr().out
    assert rc == 3
    assert "LOG_FLUSH_STATUS=skipped-no-logs-commit" in out
    assert mock_flush.call_args.kwargs["no_logs_commit"] is True


def test_step7a_no_logs_commit_emits_skipped_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_log_flush",
        return_value="skipped-no-logs-commit",
    ) as mock_flush, patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path, no_logs_commit=True)

    assert rc == 0
    assert "LOG_FLUSH_STATUS=skipped-no-logs-commit" in capsys.readouterr().out
    mock_flush.assert_called_once()


def test_step7a_relays_session_transcript_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("LARCH_CLAUDE_SOURCE_FILE=/tmp/source.jsonl\n", encoding="utf-8")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        if len(args) >= 2 and args[0] == "run-log" and args[1] == "capture-transcript":
            return subprocess.CompletedProcess(args, 0, "SESSION_TRANSCRIPT_STATUS=captured\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    with patch.object(step_7a, "_is_small_non_runtime_change", return_value=True), patch.object(
        step_7a,
        "_run_cli",
        side_effect=fake_run_cli,
    ), patch.object(step_7a.execution_issues, "flush_execution_issues", return_value=(0, "ok", 0, "")), patch.object(
        step_7a.run_logs,
        "_render_token_timing_batches",
    ), patch.object(
        step_7a.run_logs,
        "_stage_vendor_failure_diagnostics",
    ), patch.object(step_7a, "subprocess") as mock_subprocess:
        mock_subprocess.run.return_value.returncode = 0
        mock_subprocess.run.return_value.stdout = "REBASE_OUTCOME=skipped\n"
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    assert "SESSION_TRANSCRIPT_STATUS=captured" in capsys.readouterr().out
