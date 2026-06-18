"""Smoke tests for the Python /design lifecycle CLI port surfaces."""

from __future__ import annotations

import cli


EXPECTED = {
    ("design", "step2a"): ("design_lifecycle", "step2a_main"),
    ("design", "step2b-drafter"): ("design_lifecycle", "step2b_drafter_main"),
    ("design", "step2b-postplan"): ("design_lifecycle", "step2b_postplan_main"),
    ("design", "step2b5"): ("design_lifecycle", "step2b5_main"),
    ("design", "postplan-emit"): ("design_postplan", "postplan_emit_main"),
    ("design", "publish"): ("design_publish", "publish_main"),
    ("design", "log-publish"): ("design_log_publish_flow", "log_publish_main"),
    ("design", "pause-save"): ("design_pause", "pause_save_main"),
    ("design", "pause-load"): ("design_pause", "pause_load_main"),
    ("design", "render-final-summary"): ("design_summary", "render_final_summary_main"),
    ("design", "file-oos-prepare"): ("design_oos", "file_oos_prepare_main"),
    ("design", "file-oos-annotate"): ("design_oos", "file_oos_annotate_main"),
}
PLAN_EXPECTED = {
    ("plan", "validator-autofix"): ("plan_quality", "validator_autofix_main"),
}


def test_design_port_registry_entries_are_machine_stdout() -> None:
    for key, target in EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    for key, target in PLAN_EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
