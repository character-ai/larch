from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


from larch import io as larch_io
from larch.bgjob import cli, model, registry, wait
from larch.core import config, process_identity


def test_wait_done_prints_result_rows(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = model.result_env_path(tmpdir=tmp_path, step="demo-step")
    larch_io.write_kvs(path=result, values=[("BGJOB_RC", "0"), ("CUSTOM", "ok")])
    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "BGJOB_STATUS=DONE" in out
    assert "BGJOB_RC=0" in out
    assert "CUSTOM=ok" in out


def test_wait_missing_registry_reports_dead(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "BGJOB_STATUS=DEAD" in out
    assert "BGJOB_DIAG=missing-registry" in out


def test_wait_reports_wait_while_startup_marker_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    marker = model.startup_env_path(tmpdir=tmp_path, step="demo-step")
    larch_io.write_kvs(path=marker, values=[("STEP", "demo-step"), ("START_EPOCH", str(int(time.time())))])

    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=WAIT" in out
    assert "BGJOB_STATUS=DEAD" not in out


def test_wait_ignores_stale_startup_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    marker = model.startup_env_path(tmpdir=tmp_path, step="demo-step")
    larch_io.write_kvs(
        path=marker,
        values=[("STEP", "demo-step"), ("START_EPOCH", str(int(time.time()) - config.BGJOB_STARTUP_GRACE_S - 1))],
    )

    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=DEAD" in out
    assert "BGJOB_DIAG=missing-registry" in out


def test_wait_keeps_polling_when_child_is_dead_but_daemon_is_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result_path = model.result_env_path(tmpdir=tmp_path, step="demo-step")
    reg_entry = model.RegistryEntry(
        step="demo-step",
        run_id="run-1",
        tmpdir=tmp_path,
        log_dir=tmp_path / "bgjob",
        clone_path=tmp_path,
        daemon=process_identity.RecordedProcessIdentity(pid=1, pgid=1, start_time="test", command_signature="daemon"),
        child=process_identity.RecordedProcessIdentity(pid=2, pgid=2, start_time="test", command_signature="child"),
        owner=None,
        start_epoch=1,
        budget_s=1,
        stdout_log=tmp_path / "bgjob/demo-step.stdout.log",
        stderr_log=tmp_path / "bgjob/demo-step.stderr.log",
        result_env=result_path,
    )
    reg_path = tmp_path / "registry.env"

    def fake_read_for(*, tmpdir: Path, step: str, run_id: str | None = None) -> tuple[Path, model.RegistryEntry | None]:
        _ = (tmpdir, step, run_id)
        return (reg_path, reg_entry)

    def fake_daemon_liveness(_entry: model.RegistryEntry) -> model.LivenessVerdict:
        return model.LivenessVerdict(live=True, reason="ok")

    def fake_child_liveness(_entry: model.RegistryEntry) -> model.LivenessVerdict:
        return model.LivenessVerdict(live=False, reason="missing-pid")

    monkeypatch.setattr(registry, "read_for", fake_read_for)
    monkeypatch.setattr(registry, "daemon_liveness", fake_daemon_liveness)
    monkeypatch.setattr(registry, "child_liveness", fake_child_liveness)

    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=WAIT" in out
    assert "BGJOB_STATUS=DEAD" not in out


def test_wait_rechecks_result_when_registry_unlinked_after_result_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The daemon writes the result env before unlinking its registry row.

    When the registry vanishes in the window between the wait's result read and its
    registry read, the result is already on disk; the wait must re-read it instead
    of declaring a spurious DEAD missing-registry.
    """
    monkeypatch.setenv("LARCH_BGJOB_REGISTRY_ROOT", str(tmp_path / "registry"))
    result = model.result_env_path(tmpdir=tmp_path, step="demo-step")
    larch_io.write_kvs(path=result, values=[("BGJOB_RC", "timeout"), ("BGJOB_ELAPSED_S", "1")])

    real_read_result = wait._read_result  # pyright: ignore[reportPrivateUsage]  # monkeypatch private _read_result to replay the registry-unlinked-after-result-check race
    call_count = {"n": 0}

    def race_read_result(path: Path) -> dict[str, str] | None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return real_read_result(path)

    monkeypatch.setattr(wait, "_read_result", race_read_result)

    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=DONE" in out
    assert "BGJOB_RC=timeout" in out
    assert "BGJOB_STATUS=DEAD" not in out
    assert call_count["n"] >= 2
