"""Smoke tests for the Python /design lifecycle CLI port surfaces."""

from __future__ import annotations

from larch import cli


EXPECTED = {
    ("design", verb): (module, func)
    for verb, module, func in (
        ("step2b-drafter", "larch.design.design_lifecycle", "step2b_drafter_main"),
        ("step2b-postplan", "larch.design.design_lifecycle", "step2b_postplan_main"),
        ("step2b5", "larch.design.design_lifecycle", "step2b5_main"),
        ("step5b-prepare", "larch.design.design_lifecycle", "step5b_prepare_main"),
        ("step5b-annotate", "larch.design.design_lifecycle", "step5b_annotate_main"),
        ("postplan-emit", "larch.design.design_postplan", "postplan_emit_main"),
        ("publish", "larch.design.design_publish", "publish_main"),
        ("clarify", "larch.design.clarify", "design_clarify_main"),
        ("log-publish", "larch.design.design_log_publish_flow", "log_publish_main"),
        ("pause-save", "larch.design.design_pause", "pause_save_main"),
        ("pause-load", "larch.design.design_pause", "pause_load_main"),
        ("render-gate", "larch.design.design_gate_render", "render_gate_main"),
        ("render-final-summary", "larch.design.design_summary", "render_final_summary_main"),
        ("stage-terminal-state", "larch.design.design_lifecycle", "stage_terminal_state_main"),
        ("failure-report", "larch.design.design_lifecycle", "failure_report_main"),
        ("step-final-summary", "larch.design.design_lifecycle", "step_final_summary_main"),
        ("file-oos-prepare", "larch.design.design_oos", "file_oos_prepare_main"),
        ("file-oos-annotate", "larch.design.design_oos", "file_oos_annotate_main"),
    )
}
PLAN_EXPECTED = {
    ("plan", "validator-autofix"): ("larch.design.plan_quality", "validator_autofix_main"),
}
AGENT_EXPECTED = {
    ("agent", "launch-codex-drafter"): ("larch.agents.agents", "launch_codex_drafter_main"),
    ("agent", "launch-claude-drafter"): ("larch.agents.agents", "launch_claude_drafter_main"),
}
ARCHITECTURAL_GUIDELINES_EXPECTED = {
    ("architectural-guidelines", "read"): ("larch.core.architectural_guidelines", "read_main"),
    ("architectural-guidelines", "present-note"): ("larch.core.architectural_guidelines", "present_note_main"),
    ("architectural-guidelines", "materialize-diff"): ("larch.core.architectural_guidelines", "materialize_diff_main"),
    ("architectural-guidelines", "prepare"): ("larch.core.architectural_guidelines", "prepare_main"),
    ("architectural-guidelines", "prepare-compose"): ("larch.core.architectural_guidelines", "prepare_compose_main"),
    ("architectural-guidelines", "write-compose-assessment"): ("larch.core.architectural_guidelines", "write_compose_assessment_main"),
    ("architectural-guidelines", "write-staged-assessment"): ("larch.core.architectural_guidelines", "write_staged_assessment_main"),
    ("architectural-guidelines", "pin-note-from-staged"): ("larch.core.architectural_guidelines", "pin_note_from_staged_main"),
    ("architectural-guidelines", "invalidate"): ("larch.core.architectural_guidelines", "invalidate_main"),
    ("architectural-guidelines", "persist-design-assessment"): ("larch.core.architectural_guidelines", "persist_design_assessment_main"),
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
