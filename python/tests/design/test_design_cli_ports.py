"""Smoke tests for the Python /design lifecycle CLI port surfaces."""

from __future__ import annotations

from larch import cli


EXPECTED = {
    ("design", verb): (module, func, True)
    for verb, module, func in (
        ("step35-settle", "larch.design.design_settle", "step35_settle_main"),
        ("step2b5", "larch.design.design_step5c", "step2b5_main"),
        ("step5b-prepare", "larch.design.design_step5b", "step5b_prepare_main"),
        ("step5b-annotate", "larch.design.design_step5b", "step5b_annotate_main"),
        ("compose-plan-md", "larch.design.design_step5c", "compose_plan_md_main"),
        ("render-gate", "larch.design.design_gate_render", "render_gate_main"),
        ("render-final-summary", "larch.design.design_summary", "render_final_summary_main"),
        ("file-oos-prepare", "larch.design.design_oos", "file_oos_prepare_main"),
        ("file-oos-annotate", "larch.design.design_oos", "file_oos_annotate_main"),
    )
}
AGENT_EXPECTED: dict[tuple[str, str], tuple[str, str]] = {}
ARCHITECTURAL_GUIDELINES_EXPECTED = {
    ("architectural-invariants", "read"): ("larch.core.architectural_guidelines", "invariants_read_main"),
    ("architectural-guidelines", "read"): ("larch.core.architectural_guidelines", "read_main"),
    ("architectural-guidelines", "present-note"): ("larch.core.architectural_guidelines", "present_note_main"),
    ("architectural-guidelines", "materialize-diff"): ("larch.core.architectural_guidelines", "materialize_diff_main"),
    ("architectural-guidelines", "prepare"): ("larch.core.architectural_guidelines", "prepare_main"),
    ("architectural-guidelines", "prepare-compose"): ("larch.core.architectural_guidelines", "prepare_compose_main"),
    ("architectural-guidelines", "write-compose-assessment"): ("larch.core.architectural_guidelines", "write_compose_assessment_main"),
    ("architectural-guidelines", "append-deviation-note"): ("larch.core.architectural_guidelines", "append_deviation_note_main"),
    ("architectural-guidelines", "write-staged-assessment"): ("larch.core.architectural_guidelines", "write_staged_assessment_main"),
    ("architectural-guidelines", "pin-note-from-staged"): ("larch.core.architectural_guidelines", "pin_note_from_staged_main"),
    ("architectural-guidelines", "invalidate"): ("larch.core.architectural_guidelines", "invalidate_main"),
    ("architectural-guidelines", "persist-design-assessment"): ("larch.core.architectural_guidelines", "persist_design_assessment_main"),
}
ARCHITECTURAL_INVARIANTS_EXPECTED = {
    ("architectural-invariants", "present-note"): ("larch.core.architectural_guidelines", "invariants_present_note_main"),
    ("architectural-invariants", "materialize-diff"): ("larch.core.architectural_guidelines", "invariants_materialize_diff_main"),
    ("architectural-invariants", "prepare"): ("larch.core.architectural_guidelines", "invariants_prepare_main"),
    ("architectural-invariants", "prepare-compose"): ("larch.core.architectural_guidelines", "invariants_prepare_compose_main"),
    ("architectural-invariants", "write-compose-assessment"): ("larch.core.architectural_guidelines", "invariants_write_compose_assessment_main"),
    ("architectural-invariants", "append-deviation-note"): ("larch.core.architectural_guidelines", "invariants_append_deviation_note_main"),
    ("architectural-invariants", "write-staged-assessment"): ("larch.core.architectural_guidelines", "invariants_write_staged_assessment_main"),
    ("architectural-invariants", "pin-note-from-staged"): ("larch.core.architectural_guidelines", "invariants_pin_note_from_staged_main"),
    ("architectural-invariants", "invalidate"): ("larch.core.architectural_guidelines", "invariants_invalidate_main"),
    ("architectural-invariants", "persist-design-assessment"): ("larch.core.architectural_guidelines", "invariants_persist_design_assessment_main"),
}


def test_design_port_registry_entries_are_machine_stdout() -> None:
    for key, target in EXPECTED.items():
        assert cli._REGISTRY[key] == target  # pyright: ignore[reportPrivateUsage]
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    assert ("plan", "validator-autofix") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("plan-review", "step3b-entry") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    for key, target in AGENT_EXPECTED.items():
        module_name, func_name, _machine_stdout = cli._REGISTRY[key]  # pyright: ignore[reportPrivateUsage]
        assert (module_name, func_name) == target
    for key in (
        ("architectural-assessment", "materialize"),
        ("architectural-assessment", "submit"),
        ("architectural-assessment", "sanitize-detail"),
        ("architectural-assessment", "final-report-sections"),
    ):
        assert key not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    for key, target in ARCHITECTURAL_GUIDELINES_EXPECTED.items():
        module_name, func_name, machine_stdout = cli._REGISTRY[key]  # pyright: ignore[reportPrivateUsage]
        assert (module_name, func_name) == target
        assert machine_stdout is True
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
    for key, target in ARCHITECTURAL_INVARIANTS_EXPECTED.items():
        module_name, func_name, machine_stdout = cli._REGISTRY[key]  # pyright: ignore[reportPrivateUsage]
        assert (module_name, func_name) == target
        assert machine_stdout is True
        assert key in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]
