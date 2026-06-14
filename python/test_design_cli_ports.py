"""Smoke tests for the Python /design lifecycle CLI port surfaces."""

from __future__ import annotations

import cli


EXPECTED = {
    ("design", "postplan-emit"): ("design_postplan", "postplan_emit_main"),
    ("design", "publish"): ("design_publish", "publish_main"),
    ("design", "log-publish"): ("design_log_publish_flow", "log_publish_main"),
    ("design", "pause-save"): ("design_pause", "pause_save_main"),
    ("design", "pause-load"): ("design_pause", "pause_load_main"),
    ("design", "render-final-summary"): ("design_summary", "render_final_summary_main"),
    ("design", "file-oos-prepare"): ("design_oos", "file_oos_prepare_main"),
    ("design", "file-oos-annotate"): ("design_oos", "file_oos_annotate_main"),
}


def test_design_port_registry_entries_are_machine_stdout() -> None:
    for key, target in EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
