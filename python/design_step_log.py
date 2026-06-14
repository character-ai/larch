"""Python CLI entrypoint for the /implement Step 1 plan-log helper."""

from __future__ import annotations

from collections.abc import Sequence

import design_legacy


def step1_log_main(argv: Sequence[str]) -> int:
    return design_legacy.run_script("scripts/run-step1-plan-log.sh", argv)
