"""Tests for /implement Step 1 plan-log CLI registration."""

from __future__ import annotations

import cli


def test_plan_step1_log_registered_as_machine_stdout() -> None:
    assert cli._REGISTRY[("plan", "step1-log")] == ("design_step_log", "step1_log_main")  # pyright: ignore[reportPrivateUsage]
    assert ("plan", "step1-log") in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
