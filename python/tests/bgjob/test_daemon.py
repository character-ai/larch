from __future__ import annotations

import os
import subprocess
import sys
import signal
import time
from pathlib import Path
from types import SimpleNamespace
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


def test_daemon_child_clears_stale_result_and_registers_before_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    stale_result = model.result_env_path(tmpdir=tmp_path, step="demo-step")
    stale_result.parent.mkdir(parents=True, exist_ok=True)
    stale_result.write_text("BGJOB_RC=0\n", encoding="utf-8")
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

    monkeypatch.setattr(daemon.os, "setsid", lambda: None)
    monkeypatch.setattr(daemon.os, "getpgid", lambda _pid: child_identity.pgid)
    monkeypatch.setattr(daemon.os, "close", lambda _fd: None)
    monkeypatch.setattr(daemon.subprocess, "Popen", lambda *args, **kwargs: SimpleNamespace(pid=child_identity.pid))

    def capture(pid: int, expected_signature: str = "") -> process_identity.RecordedProcessIdentity:
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
        path.write_text("STEP=demo-step\nRUN_ID=run-1\n", encoding="utf-8")
        order.append("registry")
        return path

    def write_pipe(fd: int, data: bytes) -> int:
        assert order == [f"capture:{child_identity.pid}", f"capture:{os.getpid()}", "registry"]
        order.append("pipe")
        return len(data)

    def monitor(spec_arg: model.JobSpec, child_arg: object, child_identity_arg: object, reg_path: Path) -> int:
        assert spec_arg == spec
        assert child_identity_arg == child_identity
        assert reg_path.is_file()
        order.append("monitor")
        return 0

    monkeypatch.setattr(daemon, "_capture_identity", capture)
    monkeypatch.setattr(daemon.registry, "write_entry", write_entry)
    monkeypatch.setattr(daemon.os, "write", write_pipe)
    monkeypatch.setattr(daemon, "_monitor", monitor)
    monkeypatch.setattr(daemon, "_terminate_child_group", lambda *args, **kwargs: None)

    rc = daemon._daemon_child(spec, pipe_fd=99)

    assert rc == 0
    assert not stale_result.exists()
    assert order == [f"capture:{child_identity.pid}", f"capture:{os.getpid()}", "registry", "pipe", "monitor"]


def test_owner_identity_from_env_requires_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(daemon, "_read_owner_identity", lambda _raw: None)

    with pytest.raises(RuntimeError, match="owner pid 123"):
        daemon.owner_identity_from_env("123")


def test_owner_identity_from_env_uses_session_pid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = _identity(pid=123, pgid=456, signature="owner")
    seen: list[str] = []
    for name in ("LARCH_BGJOB_OWNER_PID", "LARCH_BG_POLL_GUARD_SESSION_PID", "CLAUDE_PID"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LARCH_CLAUDE_PID", "123")
    monkeypatch.setattr(
        daemon,
        "_read_owner_identity",
        lambda raw: seen.append(raw) or (identity if raw == "123" else None),
    )

    owner = daemon.owner_identity_from_env(None)

    assert owner.recorded == identity
    assert seen == ["123"]


def test_owner_identity_from_env_fails_closed_without_session_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LARCH_BGJOB_OWNER_PID", "LARCH_BG_POLL_GUARD_SESSION_PID", "LARCH_CLAUDE_PID", "CLAUDE_PID"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="missing session owner pid"):
        daemon.owner_identity_from_env(None)


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
        wait=lambda timeout=None: 0,
    )
    calls: dict[str, object] = {}
    monotonic_values = iter([0.0, 2.0, 2.0])

    monkeypatch.setattr(daemon.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(daemon, "_terminate_child_group", lambda identity, *, reason: calls.update(identity=identity, reason=reason))
    monkeypatch.setattr(daemon, "write_result", lambda *, spec, rc, elapsed_s: calls.update(rc=rc, elapsed_s=elapsed_s, spec=spec))
    monkeypatch.setattr(daemon.registry, "unlink_entry", lambda path: calls.update(unlinked=path))

    rc = daemon._monitor(spec, child, child_identity, tmp_path / "registry.env")

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
        wait=lambda timeout=None: 0,
    )
    calls: dict[str, object] = {}
    monotonic_values = iter([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    monkeypatch.setattr(daemon.config, "BGJOB_OWNER_GRACE_S", 0.0)
    monkeypatch.setattr(daemon.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(daemon.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        daemon.process_identity,
        "validate_process_identity",
        lambda *, recorded, runner=None: process_identity.ValidationResult(ok=False, reason="missing-pid"),
    )
    monkeypatch.setattr(daemon, "_terminate_child_group", lambda identity, *, reason: calls.update(identity=identity, reason=reason))
    monkeypatch.setattr(daemon, "write_result", lambda *, spec, rc, elapsed_s: calls.update(rc=rc, elapsed_s=elapsed_s, spec=spec))
    monkeypatch.setattr(daemon.registry, "unlink_entry", lambda path: calls.update(unlinked=path))

    rc = daemon._monitor(spec, child, child_identity, tmp_path / "registry.env")

    assert rc == 0
    assert calls["identity"] == child_identity
    assert calls["reason"] == "orphaned"
    assert calls["rc"] == "orphaned"
    assert calls["spec"] == spec


def test_monitor_treats_dead_child_live_daemon_as_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    child_identity = _identity(pid=111, pgid=222, signature="python -c")
    daemon_identity = _identity(pid=333, pgid=444, signature="daemon")
    spec = model.JobSpec(
        step="demo-step",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        budget_s=1,
        command=(sys.executable, "-c", "print('hello')"),
        run_id="run-1",
        owner=model.OwnerIdentity(recorded=daemon_identity),
    )
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

    monkeypatch.setattr(daemon.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(daemon.registry, "read_for", lambda *, tmpdir, step, run_id=None: (reg_path, reg_entry))
    monkeypatch.setattr(daemon.registry, "daemon_liveness", lambda entry: model.LivenessVerdict(live=True, reason="ok"))
    monkeypatch.setattr(daemon.registry, "child_liveness", lambda entry: model.LivenessVerdict(live=False, reason="missing-pid"))

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

    monkeypatch.setattr(daemon.os, "setsid", lambda: None)
    monkeypatch.setattr(daemon.os, "close", lambda _fd: None)
    monkeypatch.setattr(daemon.os, "killpg", lambda pid, sig: calls.update(killpg=(pid, sig)))
    monkeypatch.setattr(
        daemon.subprocess,
        "Popen",
        lambda *args, **kwargs: SimpleNamespace(pid=child_identity.pid, wait=lambda timeout=None: 0),
    )

    def capture(pid: int, expected_signature: str = "") -> process_identity.RecordedProcessIdentity:
        if pid == child_identity.pid:
            raise RuntimeError("child identity capture failed")
        raise AssertionError(f"unexpected pid {pid}")

    monkeypatch.setattr(daemon, "_capture_identity", capture)

    with pytest.raises(RuntimeError, match="child identity capture failed"):
        daemon._daemon_child(spec, pipe_fd=99)

    assert calls["killpg"] == (child_identity.pid, signal.SIGKILL)


def test_daemon_child_rejects_symlinked_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "bgjob"
    log_dir.mkdir()
    target = log_dir / "demo-step.stdout.target"
    target.write_text("", encoding="utf-8")
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

    monkeypatch.setattr(daemon.os, "setsid", lambda: None)
    monkeypatch.setattr(daemon.os, "close", lambda _fd: None)
    monkeypatch.setattr(daemon.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("Popen should not be reached"))

    with pytest.raises(ValueError, match="symlink"):
        daemon._daemon_child(spec, pipe_fd=99)


def test_write_result_keeps_authoritative_bgjob_rc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    merge = tmp_path / "merge.env"
    merge.write_text("BGJOB_RC=9\nCUSTOM=ok\nSTEP=bad\nBGJOB_ELAPSED_S=999\n", encoding="utf-8")
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


def test_bgjob_start_and_wait_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if process_identity.read_process_identity(pid=os.getpid()) is None:
        pytest.skip("process identity probe is unavailable in this sandbox")
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
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
