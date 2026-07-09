from __future__ import annotations

from pathlib import Path

import pytest

from larch.bgjob import cli, model
from larch.core import process_identity


def _identity(*, pid: int, pgid: int, signature: str) -> process_identity.RecordedProcessIdentity:
    return process_identity.RecordedProcessIdentity(
        pid=pid,
        pgid=pgid,
        start_time="test-start",
        command_signature=signature,
        expected_signature=signature,
    )


def _entry(tmp_path: Path) -> model.RegistryEntry:
    return model.RegistryEntry(
        step="demo-step",
        run_id="run-1",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        clone_path=tmp_path,
        daemon=_identity(pid=111, pgid=111, signature="daemon"),
        child=_identity(pid=222, pgid=222, signature="child"),
        owner=None,
        start_epoch=1,
        budget_s=1,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=tmp_path / "bgjob/demo-step.result.env",
    )


def _missing_pid_liveness(_entry_arg: model.RegistryEntry) -> model.LivenessVerdict:
    return model.LivenessVerdict(live=False, reason="missing-pid")


def _mismatched_liveness(_entry_arg: model.RegistryEntry) -> model.LivenessVerdict:
    return model.LivenessVerdict(live=False, reason="start-time-mismatch")


def _live_liveness(_entry_arg: model.RegistryEntry) -> model.LivenessVerdict:
    return model.LivenessVerdict(live=True, reason="ok")


def _expired(_entry_arg: model.RegistryEntry) -> bool:
    return True


def _not_expired(_entry_arg: model.RegistryEntry) -> bool:
    return False


def test_reap_removes_stale_dead_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reg_path = tmp_path / "registry.env"
    entry = _entry(tmp_path)
    unlinked: list[Path] = []

    monkeypatch.setattr(cli.registry, "iter_entries", lambda: [(reg_path, entry)])
    monkeypatch.setattr(cli.registry, "child_liveness", _missing_pid_liveness)
    monkeypatch.setattr(cli.registry, "daemon_liveness", _missing_pid_liveness)
    monkeypatch.setattr(cli.registry, "unlink_entry", unlinked.append)

    rc = cli.reap_main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert out == "BGJOB_REAPED=1\n"
    assert unlinked == [reg_path]


def test_reap_unlinks_expired_recycled_pid_without_direct_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reg_path = tmp_path / "registry.env"
    entry = _entry(tmp_path)
    unlinked: list[Path] = []
    terminated: list[process_identity.RecordedProcessIdentity] = []

    def fake_terminate(
        *,
        recorded: process_identity.RecordedProcessIdentity,
        log_path: Path | None,
        caller: str,
        reason: str,
    ) -> process_identity.ValidationResult:
        assert log_path is None
        assert caller == "bgjob-reap"
        assert reason == "expired-registry"
        terminated.append(recorded)
        return process_identity.ValidationResult(ok=False, reason="start-time-mismatch")

    monkeypatch.setattr(cli.registry, "iter_entries", lambda: [(reg_path, entry)])
    monkeypatch.setattr(cli.registry, "child_liveness", _mismatched_liveness)
    monkeypatch.setattr(cli.registry, "daemon_liveness", _live_liveness)
    monkeypatch.setattr(cli.registry, "entry_expired", _expired)
    monkeypatch.setattr(cli.registry, "unlink_entry", unlinked.append)
    monkeypatch.setattr(cli.process_identity, "terminate_validated_process_group", fake_terminate)

    rc = cli.reap_main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert out == "BGJOB_REAPED=1\n"
    assert terminated == [entry.child]
    assert unlinked == [reg_path]


def test_reap_preserves_live_identity_valid_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    entry = _entry(tmp_path)
    unlinked: list[Path] = []

    def fail_terminate(**_kwargs: object) -> process_identity.ValidationResult:
        pytest.fail("terminate should not be called")

    monkeypatch.setattr(cli.registry, "iter_entries", lambda: [(tmp_path / "registry.env", entry)])
    monkeypatch.setattr(cli.registry, "child_liveness", _live_liveness)
    monkeypatch.setattr(cli.registry, "daemon_liveness", _live_liveness)
    monkeypatch.setattr(cli.registry, "entry_expired", _not_expired)
    monkeypatch.setattr(cli.registry, "unlink_entry", unlinked.append)
    monkeypatch.setattr(cli.process_identity, "terminate_validated_process_group", fail_terminate)

    rc = cli.reap_main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert out == "BGJOB_REAPED=0\n"
    assert not unlinked


def test_reap_removes_invalid_registry_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reg_path = tmp_path / "invalid.env"
    unlinked: list[Path] = []

    monkeypatch.setattr(cli.registry, "iter_entries", lambda: [(reg_path, None)])
    monkeypatch.setattr(cli.registry, "unlink_entry", unlinked.append)

    rc = cli.reap_main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert out == "BGJOB_REAPED=1\n"
    assert unlinked == [reg_path]
