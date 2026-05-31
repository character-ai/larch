"""Tests for proc.run."""

from __future__ import annotations

import sys

import config
import proc


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
        timeout=0.1,
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
        timeout=0.1,
    )
    assert result.returncode == config.PROC_TIMEOUT_EXIT_CODE
    assert "partial-out" in result.stdout
    assert "partial-err" in result.stderr
