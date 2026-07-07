from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


from larch import io as larch_io
from larch.bgjob import cli, model


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
