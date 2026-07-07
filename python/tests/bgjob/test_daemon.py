from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
import pytest

from larch.core import process_identity


def _repo_cli() -> list[str]:
    return [sys.executable, str(Path(__file__).resolve().parents[2] / "cli.py")]


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
