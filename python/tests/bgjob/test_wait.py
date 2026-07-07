from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


from larch import io as larch_io
from larch.bgjob import cli, model, registry
from larch.core import process_identity


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

    monkeypatch.setattr(registry, "read_for", lambda *, tmpdir, step, run_id=None: (reg_path, reg_entry))
    monkeypatch.setattr(registry, "daemon_liveness", lambda entry: model.LivenessVerdict(live=True, reason="ok"))
    monkeypatch.setattr(registry, "child_liveness", lambda entry: model.LivenessVerdict(live=False, reason="missing-pid"))

    rc = cli.wait_main(["--step", "demo-step", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "BGJOB_STATUS=WAIT" in out
    assert "BGJOB_STATUS=DEAD" not in out
