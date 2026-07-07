from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import pytest

from larch import io as larch_io
from larch.bgjob import daemon, model
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

    def monitor(spec_arg: model.JobSpec, child_arg: object, reg_path: Path) -> int:
        assert spec_arg == spec
        assert reg_path.is_file()
        order.append("monitor")
        return 0

    monkeypatch.setattr(daemon, "_capture_identity", capture)
    monkeypatch.setattr(daemon.registry, "write_entry", write_entry)
    monkeypatch.setattr(daemon.os, "write", write_pipe)
    monkeypatch.setattr(daemon, "_monitor", monitor)

    rc = daemon._daemon_child(spec, pipe_fd=99)

    assert rc == 0
    assert not stale_result.exists()
    assert order == [f"capture:{child_identity.pid}", f"capture:{os.getpid()}", "registry", "pipe", "monitor"]


def test_owner_identity_from_env_requires_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(daemon, "_read_owner_identity", lambda _raw: None)

    with pytest.raises(RuntimeError, match="owner pid 123"):
        daemon.owner_identity_from_env("123")


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
