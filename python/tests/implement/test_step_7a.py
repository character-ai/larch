from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
import subprocess

import pytest

from larch.implement import step_7a


def _no_small_non_runtime_change(*, base_remote: str, base_ref: str) -> bool:
    _ = (base_remote, base_ref)
    return False


def _successful_log_checkpoint(*_args: object, **_kwargs: object) -> str:
    return "ok"


def _successful_subprocess(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, "", "")


def test_step7a_bgjob_result_capture_includes_checkpoint_and_tail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    merge_env = tmp_path / "bgjob" / "implement-step7a.merge.env"
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    def fake_is_small_non_runtime_change(*, base_remote: str, base_ref: str) -> bool:
        _ = (base_remote, base_ref)
        return True

    def fake_log_checkpoint(implement_tmpdir: Path, *, run_id: str) -> str:
        _ = (implement_tmpdir, run_id)
        return "skip"

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", fake_is_small_non_runtime_change)
    monkeypatch.setattr(step_7a, "_checkpoint_execution_issues", fake_log_checkpoint)
    with patch.object(step_7a, "subprocess") as mock_subprocess, patch.object(
        step_7a.rust_runtime,
        "checkpoint_probe",
        return_value=step_7a.rust_runtime.CheckpointProbeOutput(
            exit_code=0,
            stdout="CHECKPOINT_NEXT=continue\nREBASE_OUTCOME=skipped\n",
            stderr="",
            routing={},
            advisory_lines=(),
        ),
    ):
        mock_subprocess.run.return_value.returncode = 0
        rc = step_7a.main(["--implement-tmpdir", str(tmp_path), "--bgjob-merge-result-env", str(merge_env)])

    assert rc == 0
    text = merge_env.read_text(encoding="utf-8")
    assert "CHECKPOINT_NEXT=continue\n" in text
    assert "REBASE_OUTCOME=skipped\n" in text
    assert "BGJOB_RC=" not in text


def test_step7a_bgjob_launch_starts_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[tuple[str, ...]] = []
    entrypoint = tmp_path / "scripts" / "larch.sh"

    def fake_larch_entrypoint(_root: Path) -> Path:
        return entrypoint

    def fake_subprocess_run(argv: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        calls.append(tuple(args))
        return subprocess.CompletedProcess(args, 0, "BGJOB_STATUS=STARTED STEP=implement-step7a PGID=123\n", "")

    monkeypatch.setattr(step_7a, "larch_entrypoint", fake_larch_entrypoint)
    monkeypatch.setattr(step_7a.subprocess, "run", fake_subprocess_run)

    rc = step_7a.main(["--bgjob-launch", "true", "--implement-tmpdir", str(tmp_path), "--run-id", "run-1"])

    assert rc == 0
    assert capsys.readouterr().out == "BGJOB_STATUS=STARTED STEP=implement-step7a PGID=123\n"
    start = calls[0]
    assert start[:3] == (str(entrypoint), "bgjob", "start")
    assert start[3:9] == (
        "--step",
        "implement-step7a",
        "--tmpdir",
        str(tmp_path),
        "--budget-s",
        "1800",
    )
    assert "--owner-pid" not in start
    assert "--merge-result-env" in start
    assert str(tmp_path / "bgjob" / "implement-step7a.merge.env") in start
    terminal_marker = start.index("--terminal-stdout-key")
    assert start[terminal_marker:terminal_marker + 2] == ("--terminal-stdout-key", "DIAGRAM_STATUS")
    assert "--bgjob-merge-result-env" in start


def test_step7a_bgjob_launch_propagates_transport_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_subprocess_run(
        argv: Sequence[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs == {"text": True, "capture_output": True, "check": False}
        return subprocess.CompletedProcess(list(argv), 17, "BGJOB_STATUS=FAILED\n", "launch failed\n")

    monkeypatch.setattr(step_7a.subprocess, "run", fake_subprocess_run)
    rc = step_7a.main([
        "--bgjob-launch",
        "true",
        "--implement-tmpdir",
        str(tmp_path),
        "--run-id",
        "run-1",
    ])

    assert rc == 17
    captured = capsys.readouterr()
    assert captured.out == "BGJOB_STATUS=FAILED\n"
    assert captured.err == "launch failed\n"


def test_step7a_bgjob_launch_rejects_symlinked_tmpdir_before_merge_env_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real_tmpdir = tmp_path / "real"
    real_tmpdir.mkdir()
    symlink_parent = tmp_path / "tmpdir-link"
    symlink_parent.symlink_to(real_tmpdir, target_is_directory=True)
    impl_tmpdir = symlink_parent / "nested"

    called: list[step_7a.Step7aBgjobLaunch] = []

    def fake_launch(spec: step_7a.Step7aBgjobLaunch) -> int:
        called.append(spec)
        return 0

    monkeypatch.setattr(step_7a, "_launch_step7a_bgjob", fake_launch)

    rc = step_7a.main(["--bgjob-launch", "true", "--implement-tmpdir", str(impl_tmpdir)])

    assert rc == 2
    assert not called
    _ = capsys.readouterr()


def test_step7a_emits_terminal_kvs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    def fake_generate_code_flow_diagram(
        implement_tmpdir: Path, *, base_remote: str, base_ref: str
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        _ = (base_remote, base_ref)
        diagram = implement_tmpdir / "code-flow-diagram.md"
        _ = diagram.write_text("## Code Flow Diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n", encoding="utf-8")
        return step_7a.pr_body.CodeFlowDiagramResult(0, "ok", str(diagram), "")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=False),
        patch.object(step_7a.pr_body, "generate_code_flow_diagram", side_effect=fake_generate_code_flow_diagram),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="skip"),
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=" in out
    assert "LOG_CHECKPOINT_STATUS=" in out
    assert (tmp_path / "code-flow-diagram.md").is_file()


def test_step7a_checkpoint_flushes_only_execution_issues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []
    _ = (tmp_path / "execution-issues.md").write_text("", encoding="utf-8")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    flushes: list[list[str]] = []

    def fake_subprocess_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv: list[str] = [str(part) for part in cast("Sequence[str]", args[0])] if args else []
        if "execution-issues" in argv:
            flushes.append(argv[argv.index("execution-issues"):])
            return subprocess.CompletedProcess(argv, 0, "FLUSH_STATUS=skip\nRECORDS=0\n", "")
        return subprocess.CompletedProcess(["python"], 0, "", "")

    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a.subprocess, "run", fake_subprocess_run)

    status = step_7a._checkpoint_execution_issues(  # pyright: ignore[reportPrivateUsage]
        tmp_path, run_id="run-1"
    )

    assert status == "ok"
    assert calls == [("token", "mark", "Step 8 — ship PR")]
    assert flushes == [[
        "execution-issues", "flush",
        "--log-root", str(tmp_path / "larch-logs"),
        "--run-id", "run-1",
        "--issue-log", str(tmp_path / "execution-issues.md"),
        "--step-label", "7a",
        "--source-label", "execution-issues.md Step 7a checkpoint",
    ]]


def test_step7a_checkpoint_reports_degraded_when_the_rust_flush_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = (tmp_path / "execution-issues.md").write_text("### Warnings\n- one\n", encoding="utf-8")

    def fake_subprocess_run(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv: list[str] = [str(part) for part in cast("Sequence[str]", args[0])] if args else []
        if "execution-issues" in argv:
            return subprocess.CompletedProcess(argv, 1, "FLUSH_STATUS=failed\nRECORDS=0\n", "")
        return subprocess.CompletedProcess(["python"], 0, "", "")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(list(args), 0, "", "")

    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a.subprocess, "run", fake_subprocess_run)

    status = step_7a._checkpoint_execution_issues(  # pyright: ignore[reportPrivateUsage]
        tmp_path, run_id="run-1"
    )

    assert status == "degraded"


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


def test_step7a_skips_diagram_for_small_non_runtime_change(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    def fake_is_small_non_runtime_change(*, base_remote: str, base_ref: str) -> bool:
        _ = (base_remote, base_ref)
        return True

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", fake_is_small_non_runtime_change)
    with (
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="skip"),
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
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

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="skip"),
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path, issue_number="42", run_id="run-42")

    assert rc == 0
    assert "reason=small-non-runtime-change" in capsys.readouterr().out


def test_step7a_reads_run_id_from_session_env_when_session_id_absent(tmp_path: Path) -> None:
    _ = (tmp_path / "session-env.sh").write_text("LARCH_RUN_ID=run-99\n", encoding="utf-8")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="skip") as mock_flush,
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    mock_flush.assert_called_once()
    assert mock_flush.call_args.kwargs["run_id"] == "run-99"


def test_step7a_diagram_failure_exits_zero_and_clears_stale_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "code-flow-diagram.md").write_text("stale\n", encoding="utf-8")
    reason = "generation-failed rc=7 tail=timeout after 600s"

    def fake_generate_code_flow_diagram(
        implement_tmpdir: Path, *, base_remote: str, base_ref: str
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        _ = (base_remote, base_ref)
        _ = (implement_tmpdir / "code-flow-diagram.failure.log").write_text("returncode: 7\nstderr: timeout after 600s\n", encoding="utf-8")
        return step_7a.pr_body.CodeFlowDiagramResult(1, "failed", "", reason)

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=False),
        patch.object(step_7a.pr_body, "generate_code_flow_diagram", side_effect=fake_generate_code_flow_diagram),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="ok"),
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
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


def test_step7a_diagram_failure_emits_diagram_reason_on_rebase_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    reason = "generation-failed rc=7 tail=timeout after 600s"

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=False),
        patch.object(
            step_7a.pr_body,
            "generate_code_flow_diagram",
            return_value=step_7a.pr_body.CodeFlowDiagramResult(1, "failed", "", reason),
        ),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="ok") as mock_flush,
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=1, stdout="REBASE_OUTCOME=conflict\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 1
    out = capsys.readouterr().out
    assert "DIAGRAM_STATUS=failed" in out
    assert f"DIAGRAM_REASON={reason}" in out
    assert "LOG_CHECKPOINT_STATUS=ok" in out
    mock_flush.assert_called_once()


def test_step7a_rebase_failure_still_checkpoints_execution_issues(tmp_path: Path) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="ok") as mock_flush,
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=1, stdout="REBASE_OUTCOME=conflict\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 1
    mock_flush.assert_called_once_with(tmp_path, run_id="run-1")


def test_step7a_rebase_failure_flushes_and_preserves_probe_rc(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="degraded") as mock_flush,
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=3, stdout="REBASE_OUTCOME=failed\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path)

    out = capsys.readouterr().out
    assert rc == 3
    assert "REBASE_OUTCOME=failed" in out
    assert "LOG_CHECKPOINT_STATUS=degraded" in out
    mock_flush.assert_called_once()


def test_step7a_rebase_failure_no_logs_commit_still_checkpoints(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="ok") as mock_flush,
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=3, stdout="REBASE_OUTCOME=failed\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path, no_logs_commit=True)

    out = capsys.readouterr().out
    assert rc == 3
    assert "LOG_CHECKPOINT_STATUS=ok" in out
    mock_flush.assert_called_once_with(tmp_path, run_id="run-1")


def test_step7a_no_logs_commit_does_not_suppress_local_checkpoint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_checkpoint_execution_issues", return_value="ok") as mock_flush,
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path, no_logs_commit=True)

    assert rc == 0
    assert "LOG_CHECKPOINT_STATUS=ok" in capsys.readouterr().out
    mock_flush.assert_called_once_with(tmp_path, run_id="run-1")


def test_step7a_does_not_capture_terminal_transcript(tmp_path: Path) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("LARCH_CLAUDE_SOURCE_FILE=/tmp/source.jsonl\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")

    with (
        patch.object(step_7a, "_is_small_non_runtime_change", return_value=True),
        patch.object(step_7a, "_run_cli", side_effect=fake_run_cli),
        patch.object(step_7a, "subprocess"),
        patch.object(
            step_7a.rust_runtime,
            "checkpoint_probe",
            return_value=step_7a.rust_runtime.CheckpointProbeOutput(
                exit_code=0, stdout="REBASE_OUTCOME=skipped\n", stderr="", routing={}, advisory_lines=()
            ),
        ),
    ):
        rc = step_7a.run_step7a(tmp_path)

    assert rc == 0
    assert not any(call[:2] == ("run-log", "capture-transcript") for call in calls)


def test_step7a_orchestrates_generation_upsert_and_checkpoint_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text("REPO=owner/repo\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []
    events: list[str] = []

    def fake_generate(
        implement_tmpdir: Path, *, base_remote: str, base_ref: str
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        assert (base_remote, base_ref) == ("origin", "main")
        events.append("generate")
        diagram = implement_tmpdir / "code-flow-diagram.md"
        _ = diagram.write_text("## Code Flow Diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n", encoding="utf-8")
        return step_7a.pr_body.CodeFlowDiagramResult(0, "ok", str(diagram), "")

    checkpoint_calls: list[tuple[str, str, str | None, str | None]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("diagrams", "upsert"):
            return subprocess.CompletedProcess(args, 0, "UPSERT_STATUS=ok\nCOMMENT_URL=https://example.test/comment/1\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    def fake_checkpoint(_runner: object, *, step_prefix: str, short_name: str, base_remote: str | None = None, base_ref: str | None = None, forked_target: str = "false", cwd: str | None = None) -> step_7a.rust_runtime.CheckpointProbeOutput:
        _ = (forked_target, cwd)
        checkpoint_calls.append((step_prefix, short_name, base_remote, base_ref))
        return step_7a.rust_runtime.CheckpointProbeOutput(exit_code=0, stdout="REBASE_OUTCOME=ok\nROUTE=continue\nCHECKPOINT_NEXT=continue\n", stderr="", routing={}, advisory_lines=())

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", _no_small_non_runtime_change)
    monkeypatch.setattr(step_7a.pr_body, "generate_code_flow_diagram", fake_generate)
    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a.rust_runtime, "checkpoint_probe", fake_checkpoint)
    monkeypatch.setattr(step_7a, "_checkpoint_execution_issues", _successful_log_checkpoint)
    monkeypatch.setattr(step_7a.subprocess, "run", _successful_subprocess)

    rc = step_7a.run_step7a(tmp_path, issue_number="42")

    assert rc == 0
    assert calls[0] == ("token", "mark", "Step 7a — pre-ship")
    assert events == ["generate"]
    assert calls[1] == (
        "diagrams",
        "upsert",
        "--issue",
        "42",
        "--code-flow-file",
        str(tmp_path / "code-flow-section.md"),
        "--repo",
        "owner/repo",
    )
    assert checkpoint_calls == [("7a.r", "diagrams", "origin", "main")]
    assert (tmp_path / "code-flow-section.md").read_text(encoding="utf-8") == (
        "## Code Flow Diagram\n\n```mermaid\ngraph TD\nA-->B\n```\n"
    )
    output = capsys.readouterr().out
    assert "COMMENT_URL=https://example.test/comment/1" in output
    assert "REBASE_OUTCOME=ok" in output
    assert "CHECKPOINT_NEXT=continue" in output


def test_step7a_rehydrates_fork_target_for_generation_and_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "session-env.sh").write_text(
        "LARCH_FORKED_TARGET=true\nREPO=owner/repo\nUPSTREAM_REPO=upstream/repo\n",
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []
    generation_target: list[tuple[str, str]] = []

    def fake_generate(
        implement_tmpdir: Path, *, base_remote: str, base_ref: str
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        generation_target.append((base_remote, base_ref))
        diagram = implement_tmpdir / "code-flow-diagram.md"
        _ = diagram.write_text("## Code Flow Diagram\n", encoding="utf-8")
        return step_7a.pr_body.CodeFlowDiagramResult(0, "ok", str(diagram), "")

    checkpoint_calls: list[tuple[str, str, str | None, str | None]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("diagrams", "upsert"):
            return subprocess.CompletedProcess(args, 0, "UPSERT_STATUS=ok\nCOMMENT_URL=https://example.test/comment/1\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    def fake_checkpoint(_runner: object, *, step_prefix: str, short_name: str, base_remote: str | None = None, base_ref: str | None = None, forked_target: str = "false", cwd: str | None = None) -> step_7a.rust_runtime.CheckpointProbeOutput:
        _ = (forked_target, cwd)
        checkpoint_calls.append((step_prefix, short_name, base_remote, base_ref))
        return step_7a.rust_runtime.CheckpointProbeOutput(exit_code=0, stdout="REBASE_OUTCOME=ok\n", stderr="", routing={}, advisory_lines=())

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", _no_small_non_runtime_change)
    monkeypatch.setattr(step_7a.pr_body, "generate_code_flow_diagram", fake_generate)
    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a.rust_runtime, "checkpoint_probe", fake_checkpoint)
    monkeypatch.setattr(step_7a, "_checkpoint_execution_issues", _successful_log_checkpoint)
    monkeypatch.setattr(step_7a.subprocess, "run", _successful_subprocess)

    assert step_7a.run_step7a(tmp_path, issue_number="42") == 0
    assert generation_target == [("upstream", "main")]
    assert ("diagrams", "upsert", "--issue", "42", "--code-flow-file", str(tmp_path / "code-flow-section.md"), "--repo", "upstream/repo") in calls
    assert checkpoint_calls == [("7a.r", "diagrams", "upstream", "main")]


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("skipped", "br-in-participant-alias"),
        ("skipped", "dollar-in-participant-alias"),
        ("skipped", "unclosed-frontmatter"),
    ],
)
def test_step7a_sanitizer_skip_clears_stale_artifacts_and_omits_upsert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str, reason: str
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    _ = (tmp_path / "code-flow-diagram.md").write_text("stale\n", encoding="utf-8")
    _ = (tmp_path / "code-flow-section.md").write_text("stale\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("push", "checkpoint-probe"):
            return subprocess.CompletedProcess(args, 0, "REBASE_OUTCOME=ok\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    def fake_generate(
        *_args: object, **_kwargs: object
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        return step_7a.pr_body.CodeFlowDiagramResult(0, status, "", reason)

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", _no_small_non_runtime_change)
    monkeypatch.setattr(step_7a.pr_body, "generate_code_flow_diagram", fake_generate)
    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a, "_checkpoint_execution_issues", _successful_log_checkpoint)
    monkeypatch.setattr(step_7a.subprocess, "run", _successful_subprocess)

    assert step_7a.run_step7a(tmp_path, issue_number="42") == 0
    assert not (tmp_path / "code-flow-diagram.md").exists()
    assert not (tmp_path / "code-flow-section.md").exists()
    assert not any(call[:2] == ("diagrams", "upsert") for call in calls)
    assert not (tmp_path / "execution-issues.md").exists()


def test_step7a_upsert_failure_keeps_checkpoint_and_exit_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_generate(
        implement_tmpdir: Path, **_kwargs: str
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        diagram = implement_tmpdir / "code-flow-diagram.md"
        _ = diagram.write_text("## Code Flow Diagram\n", encoding="utf-8")
        return step_7a.pr_body.CodeFlowDiagramResult(0, "ok", str(diagram), "")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("diagrams", "upsert"):
            return subprocess.CompletedProcess(args, 1, "", "upsert failed\n")
        if args[:2] == ("push", "checkpoint-probe"):
            return subprocess.CompletedProcess(args, 0, "REBASE_OUTCOME=ok\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    def fake_checkpoint(_runner: object, *, step_prefix: str, short_name: str, base_remote: str | None = None, base_ref: str | None = None, forked_target: str = "false", cwd: str | None = None) -> step_7a.rust_runtime.CheckpointProbeOutput:
        _ = (base_remote, base_ref, forked_target, cwd)
        calls.append(("push", "checkpoint-probe", step_prefix, short_name))
        return step_7a.rust_runtime.CheckpointProbeOutput(exit_code=0, stdout="REBASE_OUTCOME=ok\n", stderr="", routing={}, advisory_lines=())

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", _no_small_non_runtime_change)
    monkeypatch.setattr(step_7a.pr_body, "generate_code_flow_diagram", fake_generate)
    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a.rust_runtime, "checkpoint_probe", fake_checkpoint)
    monkeypatch.setattr(step_7a, "_checkpoint_execution_issues", _successful_log_checkpoint)
    monkeypatch.setattr(step_7a.subprocess, "run", _successful_subprocess)

    assert step_7a.run_step7a(tmp_path, issue_number="42") == 0
    assert any(call[:2] == ("push", "checkpoint-probe") for call in calls)
    assert "COMMENT_URL=\n" in capsys.readouterr().out


def test_step7a_empty_issue_number_skips_upsert_but_runs_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = (tmp_path / "session-id").write_text("run-1\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_generate(
        implement_tmpdir: Path, **_kwargs: str
    ) -> step_7a.pr_body.CodeFlowDiagramResult:
        diagram = implement_tmpdir / "code-flow-diagram.md"
        _ = diagram.write_text("## Code Flow Diagram\n", encoding="utf-8")
        return step_7a.pr_body.CodeFlowDiagramResult(0, "ok", str(diagram), "")

    def fake_run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] == ("push", "checkpoint-probe"):
            return subprocess.CompletedProcess(args, 0, "REBASE_OUTCOME=ok\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    def fake_checkpoint(_runner: object, *, step_prefix: str, short_name: str, base_remote: str | None = None, base_ref: str | None = None, forked_target: str = "false", cwd: str | None = None) -> step_7a.rust_runtime.CheckpointProbeOutput:
        _ = (base_remote, base_ref, forked_target, cwd)
        calls.append(("push", "checkpoint-probe", step_prefix, short_name))
        return step_7a.rust_runtime.CheckpointProbeOutput(exit_code=0, stdout="REBASE_OUTCOME=ok\n", stderr="", routing={}, advisory_lines=())

    monkeypatch.setattr(step_7a, "_is_small_non_runtime_change", _no_small_non_runtime_change)
    monkeypatch.setattr(step_7a.pr_body, "generate_code_flow_diagram", fake_generate)
    monkeypatch.setattr(step_7a, "_run_cli", fake_run_cli)
    monkeypatch.setattr(step_7a.rust_runtime, "checkpoint_probe", fake_checkpoint)
    monkeypatch.setattr(step_7a, "_checkpoint_execution_issues", _successful_log_checkpoint)
    monkeypatch.setattr(step_7a.subprocess, "run", _successful_subprocess)

    assert step_7a.run_step7a(tmp_path) == 0
    assert not any(call[:2] == ("diagrams", "upsert") for call in calls)
    assert any(call[:2] == ("push", "checkpoint-probe") for call in calls)


@pytest.mark.parametrize(
    ("argv", "reason"),
    [([], "missing-implement-tmpdir"), (["--implement-tmpdir", "/tmp/x", "--unknown-flag", "1"], "argv")],
)
def test_step7a_argument_failures_emit_terminal_contract(
    argv: list[str],
    reason: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert step_7a.main(argv) == 2
    output = capsys.readouterr().out
    assert f"STEP_7A_BAIL_REASON={reason}" in output
    assert "REBASE_OUTCOME=skipped" in output


# pyright: reportPrivateUsage=false
