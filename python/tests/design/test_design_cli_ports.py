"""Smoke tests for the Python /design lifecycle CLI port surfaces."""

from __future__ import annotations

from larch import cli


AGENT_EXPECTED: dict[tuple[str, str], tuple[str, str]] = {}
ARCHITECTURAL_GUIDELINES_EXPECTED = {
    ("architectural-invariants", "read"): ("larch.core.architectural_guidelines", "invariants_read_main"),
    ("architectural-guidelines", "read"): ("larch.core.architectural_guidelines", "read_main"),
    ("architectural-guidelines", "present-note"): ("larch.core.architectural_guidelines", "present_note_main"),
    ("architectural-guidelines", "write-compose-assessment"): ("larch.core.architectural_guidelines", "write_compose_assessment_main"),
    ("architectural-guidelines", "append-deviation-note"): ("larch.core.architectural_guidelines", "append_deviation_note_main"),
    ("architectural-guidelines", "write-staged-assessment"): ("larch.core.architectural_guidelines", "write_staged_assessment_main"),
    ("architectural-guidelines", "pin-note-from-staged"): ("larch.core.architectural_guidelines", "pin_note_from_staged_main"),
    ("architectural-guidelines", "invalidate"): ("larch.core.architectural_guidelines", "invalidate_main"),
    ("architectural-guidelines", "persist-design-assessment"): ("larch.core.architectural_guidelines", "persist_design_assessment_main"),
}
ARCHITECTURAL_INVARIANTS_EXPECTED = {
    ("architectural-invariants", "present-note"): ("larch.core.architectural_guidelines", "invariants_present_note_main"),
    ("architectural-invariants", "write-compose-assessment"): ("larch.core.architectural_guidelines", "invariants_write_compose_assessment_main"),
    ("architectural-invariants", "append-deviation-note"): ("larch.core.architectural_guidelines", "invariants_append_deviation_note_main"),
    ("architectural-invariants", "write-staged-assessment"): ("larch.core.architectural_guidelines", "invariants_write_staged_assessment_main"),
    ("architectural-invariants", "pin-note-from-staged"): ("larch.core.architectural_guidelines", "invariants_pin_note_from_staged_main"),
    ("architectural-invariants", "invalidate"): ("larch.core.architectural_guidelines", "invariants_invalidate_main"),
    ("architectural-invariants", "persist-design-assessment"): ("larch.core.architectural_guidelines", "invariants_persist_design_assessment_main"),
}


def test_design_port_registry_entries_are_machine_stdout() -> None:
    assert ("plan", "validator-autofix") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    assert ("plan-review", "step3b-entry") not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    for key in (
        ("design", "step35-settle"),
        ("plan-review", "step35-settle"),
        ("design", "step5b-prepare"),
        ("design", "step5b-annotate"),
        ("design", "file-oos-prepare"),
        ("design", "file-oos-annotate"),
        ("design", "compose-plan-md"),
        ("design", "step2b5"),
        ("design", "step5c"),
        ("design", "step6"),
        ("design", "step6-prelude"),
        ("design", "step6-cleanup"),
        ("design", "prelude"),
        ("design", "step3-continuation-entry"),
        ("design", "dialectic-gatec"),
        ("design", "dialectic-manual"),
    ):
        assert key not in cli._REGISTRY  # pyright: ignore[reportPrivateUsage]
    for key, target in AGENT_EXPECTED.items():
        module_name, func_name, _machine_stdout = cli._REGISTRY[key]  # pyright: ignore[reportPrivateUsage]
        assert (module_name, func_name) == target
    for key in (
        ("architectural-assessment", "materialize"),
        ("architectural-assessment", "submit"),
        ("architectural-assessment", "sanitize-detail"),
        ("architectural-assessment", "final-report-sections"),
        ("architectural-guidelines", "materialize-diff"),
        ("architectural-guidelines", "prepare"),
        ("architectural-guidelines", "prepare-compose"),
        ("architectural-invariants", "materialize-diff"),
        ("architectural-invariants", "prepare"),
        ("architectural-invariants", "prepare-compose"),
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
