from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


from larch.bgjob import model, registry
from larch.core import process_identity


def _identity() -> process_identity.RecordedProcessIdentity:
    return process_identity.RecordedProcessIdentity(
        pid=os.getpid(),
        pgid=os.getpgid(os.getpid()),
        start_time="test-start",
        command_signature="pytest",
        expected_signature="",
    )


def test_registry_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    identity = _identity()
    entry = model.RegistryEntry(
        step="demo-step",
        run_id="run-1",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        clone_path=Path.cwd().resolve(),
        daemon=identity,
        child=identity,
        owner=None,
        start_epoch=1,
        budget_s=30,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=tmp_path / "bgjob/demo-step.result.env",
    )
    entry.log_dir.mkdir(parents=True, exist_ok=True)
    path = registry.write_entry(entry)
    loaded = registry.read_entry(path)
    assert loaded is not None
    assert loaded.step == "demo-step"
    assert loaded.child.pid == os.getpid()


def test_registry_ignores_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    root = model.registry_root()
    target = tmp_path / "target.env"
    _ = target.write_text("STEP=demo\n", encoding="utf-8")
    link = root / "run-demo.env"
    _ = link.symlink_to(target)
    assert registry.read_entry(link) is None


def test_registry_rejects_escaped_result_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    identity = _identity()
    entry = model.RegistryEntry(
        step="demo-step",
        run_id="run-1",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        clone_path=Path.cwd().resolve(),
        daemon=identity,
        child=identity,
        owner=None,
        start_epoch=1,
        budget_s=30,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=tmp_path.parent / "escape.env",
    )
    entry.log_dir.mkdir(parents=True, exist_ok=True)
    path = registry.write_entry(entry)

    assert registry.read_entry(path) is None


def test_default_run_id_depends_only_on_tmpdir(tmp_path: Path) -> None:
    left = model.default_run_id(tmpdir=tmp_path, clone_path=Path("/tmp/left"))
    right = model.default_run_id(tmpdir=tmp_path, clone_path=Path("/tmp/right"))

    assert left == right
