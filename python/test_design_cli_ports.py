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
        ("stage-terminal-state", "design_lifecycle", "stage_terminal_state_main"),
        ("failure-report", "design_lifecycle", "failure_report_main"),
        ("step-final-summary", "design_lifecycle", "step_final_summary_main"),
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
ARCHITECTURAL_GUIDELINES_EXPECTED = {
    ("architectural-guidelines", "read"): ("architectural_guidelines", "read_main"),
    ("architectural-guidelines", "present-note"): ("architectural_guidelines", "present_note_main"),
    ("architectural-guidelines", "materialize-diff"): ("architectural_guidelines", "materialize_diff_main"),
    ("architectural-guidelines", "prepare"): ("architectural_guidelines", "prepare_main"),
    ("architectural-guidelines", "write-staged-assessment"): ("architectural_guidelines", "write_staged_assessment_main"),
    ("architectural-guidelines", "pin-note-from-staged"): ("architectural_guidelines", "pin_note_from_staged_main"),
    ("architectural-guidelines", "invalidate"): ("architectural_guidelines", "invalidate_main"),
    ("architectural-guidelines", "persist-design-assessment"): ("architectural_guidelines", "persist_design_assessment_main"),
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
    for key, target in ARCHITECTURAL_GUIDELINES_EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
