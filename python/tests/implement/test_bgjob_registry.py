from __future__ import annotations

import os
from pathlib import Path
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


def test_write_merge_result_env_confines_and_validates_rows(tmp_path: Path) -> None:
    output = tmp_path / "bgjob" / "merge.env"
    registry.write_merge_result_env(
        path=output,
        tmpdir=tmp_path,
        rows=[("STATUS", "done"), ("ROUND", 3)],
    )
    assert output.read_text(encoding="utf-8") == "STATUS=done\nROUND=3\n"
    with pytest.raises(ValueError, match="value contains newline"):
        registry.write_merge_result_env(
            path=output,
            tmpdir=tmp_path,
            rows=[("STATUS", "bad\nvalue")],
        )
    with pytest.raises(OSError, match="escapes DESIGN_TMPDIR"):
        registry.write_merge_result_env(
            path=tmp_path.parent / "outside.env",
            tmpdir=tmp_path,
            rows=[("STATUS", "bad")],
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
        heartbeat_epoch=1,
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
    assert loaded.heartbeat_epoch == 1

    legacy = "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.startswith("HEARTBEAT_EPOCH=")
    )
    _ = path.write_text(f"{legacy}\n", encoding="utf-8")
    loaded_legacy = registry.read_entry(path)
    assert loaded_legacy is not None
    assert loaded_legacy.heartbeat_epoch == loaded_legacy.start_epoch


@pytest.mark.parametrize(
    ("heartbeat_epoch", "now", "expected"),
    [
        (14_401, 14_400.0, False),
        (14_399, 14_400.0, False),
        (14_399, 14_430.0, True),
    ],
)
def test_registry_expiry_uses_heartbeat_staleness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    heartbeat_epoch: int,
    now: float,
    expected: bool,
) -> None:
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
        heartbeat_epoch=heartbeat_epoch,
        budget_s=2,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=tmp_path / "bgjob/demo-step.result.env",
    )
    monkeypatch.setattr(registry.time, "time", lambda: now)

    assert registry.entry_expired(entry) is expected


def test_registry_round_trip_accepts_uppercase_uuid_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    identity = _identity()
    entry = model.RegistryEntry(
        step="demo-step",
        run_id="A0B1C2D3-E4F5-6789-ABCD-0123456789AB",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        clone_path=Path.cwd().resolve(),
        daemon=identity,
        child=identity,
        owner=None,
        start_epoch=1,
        heartbeat_epoch=1,
        budget_s=30,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=tmp_path / "bgjob/demo-step.result.env",
    )
    entry.log_dir.mkdir(parents=True, exist_ok=True)

    loaded = registry.read_entry(registry.write_entry(entry))

    assert loaded is not None
    assert loaded.run_id == entry.run_id


def test_registry_round_trip_accepts_external_log_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    identity = _identity()
    log_dir = tmp_path.parent / f"{tmp_path.name}-external-logs"
    log_dir.mkdir()
    entry = model.RegistryEntry(
        step="demo-step",
        run_id="run-1",
        tmpdir=tmp_path,
        log_dir=log_dir,
        clone_path=Path.cwd().resolve(),
        daemon=identity,
        child=identity,
        owner=None,
        start_epoch=1,
        heartbeat_epoch=1,
        budget_s=30,
        stdout_log=log_dir / "demo-step.stdout.log",
        stderr_log=log_dir / "demo-step.stderr.log",
        result_env=tmp_path / "bgjob/demo-step.result.env",
    )

    loaded = registry.read_entry(registry.write_entry(entry))

    assert loaded is not None
    assert loaded.log_dir == log_dir


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
        heartbeat_epoch=1,
        budget_s=30,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=tmp_path.parent / "escape.env",
    )
    entry.log_dir.mkdir(parents=True, exist_ok=True)
    path = registry.write_entry(entry)

    assert registry.read_entry(path) is None


def test_result_env_path_rejects_symlinked_bgjob_dir(tmp_path: Path) -> None:
    outside = tmp_path.parent / "bgjob-outside"
    outside.mkdir()
    (tmp_path / "bgjob").symlink_to(outside)

    with pytest.raises(ValueError, match="bgjob dir"):
        _ = model.result_env_path(tmpdir=tmp_path, step="demo-step")


def test_default_run_id_depends_only_on_tmpdir(tmp_path: Path) -> None:
    left = model.default_run_id(tmpdir=tmp_path, clone_path=Path("/tmp/left"))
    right = model.default_run_id(tmpdir=tmp_path, clone_path=Path("/tmp/right"))

    assert left == right


def test_read_for_uses_persisted_larch_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """read_for prefers LARCH_RUN_ID from session state over the tmpdir-hash default."""
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    _ = (tmp_path / "session-env.sh").write_text(
        "LARCH_RUN_ID=custom-uuid-run\n", encoding="utf-8"
    )

    path, _entry = registry.read_for(tmpdir=tmp_path, step="demo-step")

    expected_path = model.registry_path(run_id="custom-uuid-run", step="demo-step")
    assert path == expected_path


def test_read_for_explicit_run_id_overrides_session_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit run_id to read_for takes precedence over any persisted value."""
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    _ = (tmp_path / "session-env.sh").write_text(
        "LARCH_RUN_ID=ignored-run\n", encoding="utf-8"
    )

    path, _entry = registry.read_for(tmpdir=tmp_path, step="demo-step", run_id="explicit-run")

    expected_path = model.registry_path(run_id="explicit-run", step="demo-step")
    assert path == expected_path
