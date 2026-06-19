"""Smoke tests for the Python /design lifecycle CLI port surfaces."""

from __future__ import annotations

import cli


EXPECTED = {
    ("design", verb): (module, func)
    for verb, module, func in (
        ("step2a", "design_lifecycle", "step2a_main"),
        ("step2b-drafter", "design_lifecycle", "step2b_drafter_main"),
        ("step2b-postplan", "design_lifecycle", "step2b_postplan_main"),
        ("step2b5", "design_lifecycle", "step2b5_main"),
        ("step5b-prepare", "design_lifecycle", "step5b_prepare_main"),
        ("step5b-annotate", "design_lifecycle", "step5b_annotate_main"),
        ("postplan-emit", "design_postplan", "postplan_emit_main"),
        ("publish", "design_publish", "publish_main"),
        ("clarify", "clarify", "design_clarify_main"),
        ("log-publish", "design_log_publish_flow", "log_publish_main"),
        ("pause-save", "design_pause", "pause_save_main"),
        ("pause-load", "design_pause", "pause_load_main"),
        ("render-final-summary", "design_summary", "render_final_summary_main"),
        ("file-oos-prepare", "design_oos", "file_oos_prepare_main"),
        ("file-oos-annotate", "design_oos", "file_oos_annotate_main"),
    )
}
PLAN_EXPECTED = {
    ("plan", "validator-autofix"): ("plan_quality", "validator_autofix_main"),
}
AGENT_EXPECTED = {
    ("agent", "launch-codex-drafter"): ("agents", "launch_codex_drafter_main"),
    ("agent", "launch-claude-drafter"): ("agents", "launch_claude_drafter_main"),
}


def test_design_port_registry_entries_are_machine_stdout() -> None:
    for key, target in EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    for key, target in PLAN_EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    for key, target in AGENT_EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
