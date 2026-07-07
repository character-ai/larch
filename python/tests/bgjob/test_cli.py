from __future__ import annotations

from pathlib import Path
import pytest

from larch.bgjob import cli, model
from larch.core import config


def test_rejects_bad_step_slug(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.wait_main(["--step", "../bad", "--tmpdir", str(tmp_path), "--max-wait-s", "0"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "BGJOB_ERROR" in out


def test_wait_rejects_too_large_chunk(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.wait_main([
        "--step",
        "demo-step",
        "--tmpdir",
        str(tmp_path),
        "--max-wait-s",
        str(config.BGJOB_WAIT_MAX_CHUNK_S + 1),
    ])
    out = capsys.readouterr().out
    assert rc == 2
    assert "max-wait-too-large" in out


def test_model_rejects_path_escape_slug() -> None:
    with pytest.raises(ValueError, match="invalid step"):
        _ = model.validate_slug("bad/step", label="step")
