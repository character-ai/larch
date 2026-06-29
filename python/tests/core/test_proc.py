"""Tests for proc.run."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from larch.core import config
from larch.core import proc


def test_run_true_success() -> None:
    result = proc.run([sys.executable, "-c", "print('ok')"], timeout=5.0)
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
    assert result.duration >= 0.0


def test_run_false_nonzero() -> None:
    result = proc.run(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        timeout=5.0,
    )
    assert result.returncode == 3


def test_run_timeout_returns_configured_rc() -> None:
    result = proc.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout=1.0,
    )
    assert result.returncode == config.PROC_TIMEOUT_EXIT_CODE


def test_run_timeout_captures_partial_output() -> None:
    result = proc.run(
        [
            sys.executable,
            "-u",
            "-c",
            "import sys, time; print('partial-out', flush=True); "
            "print('partial-err', file=sys.stderr, flush=True); time.sleep(5)",
        ],
        timeout=1.0,
    )
    assert result.returncode == config.PROC_TIMEOUT_EXIT_CODE
    assert "partial-out" in result.stdout
    assert "partial-err" in result.stderr


def test_run_redirects_to_fd(tmp_path: Path) -> None:
    log_file = tmp_path / "out.log"
    fd = os.open(log_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
    try:
        result = proc.run(
            [sys.executable, "-c", "print('fd-test', flush=True)"],
            stdout=fd,
            stderr=fd,
        )
        assert result.returncode == 0
        assert "fd-test" in log_file.read_text(encoding="utf-8")
    finally:
        os.close(fd)
