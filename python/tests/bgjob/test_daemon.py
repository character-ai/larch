from __future__ import annotations

import os
import subprocess
import sys
import signal
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast
import pytest

from larch import io as larch_io
from larch.bgjob import daemon, model, wait
from larch.core import process_identity


def _repo_cli() -> list[str]:
    return [sys.executable, str(Path(__file__).resolve().parents[2] / "cli.py")]


def _identity(*, pid: int, pgid: int, signature: str) -> process_identity.RecordedProcessIdentity:
    return process_identity.RecordedProcessIdentity(
        pid=pid,
        pgid=pgid,
        start_time="test-start",
        command_signature=signature,
        expected_signature=signature,
    )


def _wait_ok(timeout: float | None = None) -> int:
    _ = timeout
    return 0


def _close_fd(_fd: int) -> None:
    """Stand-in for os.close in daemon tests."""


def _sleep_noop(_seconds: float) -> None:
    """Stand-in for time.sleep in daemon tests."""


def test_daemon_child_clears_stale_result_and_registers_before_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    stale_result = model.result_env_path(tmpdir=tmp_path, step="demo-step")
    stale_result.parent.mkdir(parents=True, exist_ok=True)
    _ = stale_result.write_text("BGJOB_RC=0\n", encoding="utf-8")
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    daemon_identity = _identity(pid=333, pgid=444, signature="daemon")
    order: list[str] = []

    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=daemon_identity),
    )

    def fake_getpgid(_pid: int) -> int:
        return child_identity.pgid

    def fake_popen(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(pid=child_identity.pid)

    monkeypatch.setattr(daemon.os, "setsid", lambda: None)
    monkeypatch.setattr(daemon.os, "getpgid", fake_getpgid)
    monkeypatch.setattr(daemon.os, "close", _close_fd)
    monkeypatch.setattr(daemon.subprocess, "Popen", fake_popen)

    def capture(pid: int, expected_signature: str = "") -> process_identity.RecordedProcessIdentity:
        _ = expected_signature
        order.append(f"capture:{pid}")
        if pid == child_identity.pid:
            return child_identity
        if pid == os.getpid():
            return daemon_identity
        raise AssertionError(f"unexpected pid {pid}")

    def write_entry(entry: model.RegistryEntry) -> Path:
        assert not stale_result.exists()
        path = tmp_path / "registry" / f"{entry.run_id}-{entry.step}.env"
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("STEP=demo-step\nRUN_ID=run-1\n", encoding="utf-8")
        order.append("registry")
        return path

    def write_pipe(_fd: int, data: bytes) -> int:
        assert order == [f"capture:{child_identity.pid}", f"capture:{os.getpid()}", "registry"]
        order.append("pipe")
        return len(data)

    def monitor(spec_arg: model.JobSpec, _child_arg: object, child_identity_arg: object, reg_path: Path) -> int:
        assert spec_arg == spec
        assert child_identity_arg == child_identity
        assert reg_path.is_file()
        order.append("monitor")
        return 0

    monkeypatch.setattr(daemon, "_capture_identity", capture)
    monkeypatch.setattr(daemon.registry, "write_entry", write_entry)
    monkeypatch.setattr(daemon.os, "write", write_pipe)
    monkeypatch.setattr(daemon, "_monitor", monitor)
    def fake_terminate_noop(*_args: object, **_kwargs: object) -> None:
        """Stand-in for _terminate_child_group."""

    monkeypatch.setattr(daemon, "_terminate_child_group", fake_terminate_noop)

    rc = daemon._daemon_child(spec, pipe_fd=99)  # pyright: ignore[reportPrivateUsage]

    assert rc == 0
    assert not stale_result.exists()
    assert order == [f"capture:{child_identity.pid}", f"capture:{os.getpid()}", "registry", "pipe", "monitor"]


def test_owner_identity_from_env_requires_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_owner(_raw: str) -> process_identity.RecordedProcessIdentity | None:
        """Simulate a missing owner process."""

    monkeypatch.setattr(daemon, "_read_owner_identity", fake_read_owner)

    with pytest.raises(RuntimeError, match="owner pid 123"):
        _ = daemon.owner_identity_from_env("123")


def test_owner_identity_from_env_uses_session_pid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = _identity(pid=123, pgid=456, signature="owner")
    seen: list[str] = []
    for name in ("LARCH_BGJOB_OWNER_PID", "LARCH_BG_POLL_GUARD_SESSION_PID", "CLAUDE_PID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LARCH_CLAUDE_PID", "123")
    def fake_read_owner(raw: str) -> process_identity.RecordedProcessIdentity | None:
        seen.append(raw)
        return identity if raw == "123" else None

    monkeypatch.setattr(daemon, "_read_owner_identity", fake_read_owner)

    owner = daemon.owner_identity_from_env(None)

    assert owner.recorded == identity
    assert seen == ["123"]


def test_owner_identity_from_env_fails_closed_without_session_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LARCH_BGJOB_OWNER_PID", "LARCH_BG_POLL_GUARD_SESSION_PID", "LARCH_CLAUDE_PID", "CLAUDE_PID"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="missing session owner pid"):
        _ = daemon.owner_identity_from_env(None)


def test_monitor_uses_recorded_child_identity_on_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=1,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=None),
    )
    child = SimpleNamespace(
        poll=lambda: None,
        wait=_wait_ok,
    )
    calls: dict[str, object] = {}
    monotonic_values = iter([0.0, 2.0, 2.0])

    def fake_terminate(identity: process_identity.RecordedProcessIdentity, *, reason: str) -> None:
        calls.update(identity=identity, reason=reason)

    def fake_write_result(*, spec: model.JobSpec, rc: str, elapsed_s: int) -> None:
        calls.update(rc=rc, elapsed_s=elapsed_s, spec=spec)

    def fake_unlink(path: Path) -> None:
        calls.update(unlinked=path)

    monkeypatch.setattr(daemon.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon.time, "sleep", _sleep_noop)
    monkeypatch.setattr(daemon, "_terminate_child_group", fake_terminate)
    monkeypatch.setattr(daemon, "write_result", fake_write_result)
    monkeypatch.setattr(daemon.registry, "unlink_entry", fake_unlink)

    popen_child = cast("subprocess.Popen[bytes]", child)
    rc = daemon._monitor(spec, popen_child, child_identity, tmp_path / "registry.env")  # pyright: ignore[reportPrivateUsage]

    assert rc == 0
    assert calls["identity"] == child_identity
    assert calls["reason"] == "timeout"
    assert calls["rc"] == "timeout"
    assert calls["spec"] == spec


def test_monitor_uses_recorded_child_identity_on_orphan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    owner_identity = _identity(pid=333, pgid=444, signature="owner")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=owner_identity),
    )
    child = SimpleNamespace(
        poll=lambda: None,
        wait=_wait_ok,
    )
    calls: dict[str, object] = {}
    monotonic_values = iter([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def fake_validate(*, recorded: process_identity.RecordedProcessIdentity, runner: object = None) -> process_identity.ValidationResult:
        _ = (recorded, runner)
        return process_identity.ValidationResult(ok=False, reason="missing-pid")

    def fake_terminate(identity: process_identity.RecordedProcessIdentity, *, reason: str) -> None:
        calls.update(identity=identity, reason=reason)

    def fake_write_result(*, spec: model.JobSpec, rc: str, elapsed_s: int) -> None:
        calls.update(rc=rc, elapsed_s=elapsed_s, spec=spec)

    def fake_unlink(path: Path) -> None:
        calls.update(unlinked=path)

    monkeypatch.setattr(daemon.config, "BGJOB_OWNER_GRACE_S", 0.0)
    monkeypatch.setattr(daemon.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon.time, "sleep", _sleep_noop)
    monkeypatch.setattr(daemon.process_identity, "validate_process_identity", fake_validate)
    monkeypatch.setattr(daemon, "_terminate_child_group", fake_terminate)
    monkeypatch.setattr(daemon, "write_result", fake_write_result)
    monkeypatch.setattr(daemon.registry, "unlink_entry", fake_unlink)

    popen_child = cast("subprocess.Popen[bytes]", child)
    rc = daemon._monitor(spec, popen_child, child_identity, tmp_path / "registry.env")  # pyright: ignore[reportPrivateUsage]

    assert rc == 0
    assert calls["identity"] == child_identity
    assert calls["reason"] == "orphaned"
    assert calls["rc"] == "orphaned"
    assert calls["spec"] == spec
    stderr_text = (tmp_path / "bgjob/demo-step.stderr.log").read_text(encoding="utf-8")
    assert "BGJOB_ORPHAN_REASON=missing-pid" in stderr_text
    assert "OWNER_FAILURE_COUNT=3" in stderr_text


def test_monitor_starts_owner_grace_after_consecutive_validation_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    owner_identity = _identity(pid=333, pgid=444, signature="owner")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=owner_identity),
    )
    child = SimpleNamespace(
        poll=lambda: None,
        wait=_wait_ok,
    )
    calls: dict[str, object] = {}
    validations: list[process_identity.ValidationResult] = [
        process_identity.ValidationResult(ok=False, reason="missing-pid"),
        process_identity.ValidationResult(ok=False, reason="identity-probe-timeout"),
        process_identity.ValidationResult(ok=True, reason="ok"),
        process_identity.ValidationResult(ok=False, reason="missing-pid"),
        process_identity.ValidationResult(ok=False, reason="missing-pid"),
        process_identity.ValidationResult(ok=False, reason="identity-probe-timeout"),
    ]
    monotonic_values = iter([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 5.0])

    def fake_validate(*, recorded: process_identity.RecordedProcessIdentity, runner: object = None) -> process_identity.ValidationResult:
        _ = (recorded, runner)
        return validations.pop(0)

    def fake_terminate(identity: process_identity.RecordedProcessIdentity, *, reason: str) -> None:
        calls.update(identity=identity, reason=reason)

    def fake_write_result(*, spec: model.JobSpec, rc: str, elapsed_s: int) -> None:
        calls.update(rc=rc, elapsed_s=elapsed_s, spec=spec)

    def fake_unlink(path: Path) -> None:
        calls.update(unlinked=path)

    monkeypatch.setattr(daemon.config, "BGJOB_OWNER_GRACE_S", 0.0)
    monkeypatch.setattr(daemon.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon.time, "sleep", _sleep_noop)
    monkeypatch.setattr(daemon.process_identity, "validate_process_identity", fake_validate)
    monkeypatch.setattr(daemon, "_terminate_child_group", fake_terminate)
    monkeypatch.setattr(daemon, "write_result", fake_write_result)
    monkeypatch.setattr(daemon.registry, "unlink_entry", fake_unlink)

    popen_child = cast("subprocess.Popen[bytes]", child)
    rc = daemon._monitor(spec, popen_child, child_identity, tmp_path / "registry.env")  # pyright: ignore[reportPrivateUsage]

    assert rc == 0
    assert not validations
    assert calls["identity"] == child_identity
    assert calls["reason"] == "orphaned"
    assert calls["rc"] == "orphaned"
    stderr_text = (tmp_path / "bgjob/demo-step.stderr.log").read_text(encoding="utf-8")
    assert "BGJOB_ORPHAN_REASON=identity-probe-timeout" in stderr_text
    assert "OWNER_FAILURE_COUNT=3" in stderr_text


def test_monitor_treats_dead_child_live_daemon_as_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    daemon_identity = _identity(pid=333, pgid=444, signature="daemon")
    result_path = model.result_env_path(tmpdir=tmp_path, step="demo-step")
    reg_path = tmp_path / "registry.env"
    reg_entry = model.RegistryEntry(
        step="demo-step",
        run_id="run-1",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        clone_path=tmp_path,
        daemon=daemon_identity,
        child=child_identity,
        owner=daemon_identity,
        start_epoch=1,
        budget_s=1,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=result_path,
    )

    def fake_read_for(*, tmpdir: Path, step: str, run_id: str | None = None) -> tuple[Path, model.RegistryEntry | None]:
        _ = (tmpdir, step, run_id)
        return (reg_path, reg_entry)

    def fake_daemon_liveness(_entry: model.RegistryEntry) -> model.LivenessVerdict:
        return model.LivenessVerdict(live=True, reason="ok")

    def fake_child_liveness(_entry: model.RegistryEntry) -> model.LivenessVerdict:
        return model.LivenessVerdict(live=False, reason="missing-pid")

    monkeypatch.setattr(daemon.time, "sleep", _sleep_noop)
    monkeypatch.setattr(daemon.registry, "read_for", fake_read_for)
    monkeypatch.setattr(daemon.registry, "daemon_liveness", fake_daemon_liveness)
    monkeypatch.setattr(daemon.registry, "child_liveness", fake_child_liveness)

    rc = wait.wait_once(tmpdir=tmp_path, step="demo-step", max_wait_s=0, poll_interval_s=0)
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=WAIT" in out
    assert "BGJOB_STATUS=DEAD" not in out


def test_daemon_child_kills_child_group_on_post_popen_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=None),
    )
    calls: dict[str, object] = {}

    def fake_killpg(pid: int, sig: int) -> None:
        calls.update(killpg=(pid, sig))

    def fake_popen(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(pid=child_identity.pid, wait=_wait_ok)

    monkeypatch.setattr(daemon.os, "setsid", lambda: None)
    monkeypatch.setattr(daemon.os, "close", _close_fd)
    monkeypatch.setattr(daemon.os, "killpg", fake_killpg)
    monkeypatch.setattr(daemon.subprocess, "Popen", fake_popen)

    def capture(pid: int, expected_signature: str = "") -> process_identity.RecordedProcessIdentity:
        _ = expected_signature
        if pid == child_identity.pid:
            raise RuntimeError("child identity capture failed")
        raise AssertionError(f"unexpected pid {pid}")

    monkeypatch.setattr(daemon, "_capture_identity", capture)

    with pytest.raises(RuntimeError, match="child identity capture failed"):
        _ = daemon._daemon_child(spec, pipe_fd=99)  # pyright: ignore[reportPrivateUsage]

    assert calls["killpg"] == (child_identity.pid, signal.SIGKILL)


def test_daemon_child_rejects_symlinked_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "bgjob"
    log_dir.mkdir()
    target = log_dir / "demo-step.stdout.target"
    _ = target.write_text("", encoding="utf-8")
    (log_dir / "demo-step.stdout.log").symlink_to(target)
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=log_dir,
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=None),
    )

    def fail_popen(*_args: object, **_kwargs: object) -> SimpleNamespace:
        pytest.fail("Popen should not be reached")

    monkeypatch.setattr(daemon.os, "setsid", lambda: None)
    monkeypatch.setattr(daemon.os, "close", _close_fd)
    monkeypatch.setattr(daemon.subprocess, "Popen", fail_popen)

    with pytest.raises(ValueError, match="symlink"):
        _ = daemon._daemon_child(spec, pipe_fd=99)  # pyright: ignore[reportPrivateUsage]


def test_write_result_keeps_authoritative_bgjob_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    merge = tmp_path / "merge.env"
    _ = merge.write_text("BGJOB_RC=9\nCUSTOM=ok\nSTEP=bad\nBGJOB_ELAPSED_S=999\n", encoding="utf-8")
    identity = _identity(pid=111, pgid=222, signature="daemon")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=identity),
        merge_result_env=merge,
    )

    daemon.write_result(spec=spec, rc="0", elapsed_s=7)

    rows = larch_io.read_kvs(model.result_env_path(tmpdir=tmp_path, step="demo-step"), reject_symlink=True, on_error_default=True)
    assert rows["BGJOB_RC"] == "0"
    assert rows["BGJOB_ELAPSED_S"] == "7"
    assert rows["STEP"] == "demo-step"
    assert rows["CUSTOM"] == "ok"


def test_write_result_merges_whitespace_packed_relay_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    merge = tmp_path / "merge.env"
    _ = merge.write_text(
        "STATUS=fail FAILURE_REASON=checks-failed EXIT_CODE=1 PHASE=checks DIGEST_FILE=/tmp/digest REDACTED_LOG_FILE=/tmp/redacted\n"
        "MESSAGE=hello world\n",
        encoding="utf-8",
    )
    identity = _identity(pid=111, pgid=222, signature="daemon")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=10,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=identity),
        merge_result_env=merge,
    )

    daemon.write_result(spec=spec, rc="0", elapsed_s=7)

    rows = larch_io.read_kvs(model.result_env_path(tmpdir=tmp_path, step="demo-step"), reject_symlink=True, on_error_default=True)
    assert rows["BGJOB_RC"] == "0"
    assert rows["STATUS"] == "fail"
    assert rows["FAILURE_REASON"] == "checks-failed"
    assert rows["EXIT_CODE"] == "1"
    assert rows["PHASE"] == "checks"
    assert rows["DIGEST_FILE"] == "/tmp/digest"
    assert rows["REDACTED_LOG_FILE"] == "/tmp/redacted"
    assert rows["MESSAGE"] == "hello world"


def test_bgjob_start_and_wait_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if process_identity.read_process_identity(pid=os.getpid()) is None:
        pytest.skip("process identity probe is unavailable in this sandbox")
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("LARCH_BGJOB_OWNER_PID", str(os.getpid()))
    cmd = [
        *_repo_cli(),
        "bgjob",
        "start",
        "--step",
        "demo-step",
        "--tmpdir",
        str(tmp_path),
        "--budget-s",
        "10",
        "--",
        sys.executable,
        "-c",
        "print('hello from child')",
    ]
    start = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert start.returncode == 0, start.stdout + start.stderr
    assert start.stdout.startswith("BGJOB_STATUS=STARTED STEP=demo-step PGID=")
    deadline = time.time() + 5
    out = ""
    while time.time() < deadline:
        wait = subprocess.run(
            [*_repo_cli(), "bgjob", "wait", "--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"],
            check=False,
            capture_output=True,
            text=True,
        )
        out = wait.stdout
        if "BGJOB_STATUS=DONE" in out:
            break
        time.sleep(0.2)
    assert "BGJOB_STATUS=DONE" in out
    assert "BGJOB_RC=0" in out
    assert "hello from child" in (tmp_path / "bgjob/demo-step.stdout.log").read_text(encoding="utf-8")
