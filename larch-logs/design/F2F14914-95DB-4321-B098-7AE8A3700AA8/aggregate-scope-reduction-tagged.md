### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Drop pause final-summary rendering from this fix. Scenario: The binding issue is terminal /design final report output. Pause snapshots are non-terminal; adding a pause outcome, upsert-suppression wiring, and pause-only tests expands scope beyond restoring terminal logs and tracking comments.
- **Proposed resolution**: Limit the change to publish_core, clarify, and Step 5c delegation. Leave pause log-publish unchanged in this PR; file a follow-up if pause snapshots need final-summary.md.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Pause snapshot final-summary rendering is outside the terminal final-report bug. Scenario: [DESIGNING] pause is a non-terminal checkpoint. It does not restore the missing terminal chat/report output operators reported, but it adds a new pause outcome, upsert-suppression branching, pause-save tests, and committed pause artifacts beyond the minimum fix.
- **Proposed resolution**: Limit the first fix to terminal paths (`design_publish.py` approved/failed-plan-write, `clarify.py`, Step 5c). Defer pause `final-summary.md` work to a follow-up issue unless pause snapshots are explicitly in scope.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Drop pause-save final-summary rendering from this fix. Scenario: Pause is a non-terminal checkpoint; the binding bug is missing terminal final report output and enriched committed logs on approved/failed-plan-write/clarify paths. Pause work adds a new outcome token, upsert-suppression branching, helper wiring, and pause-only tests beyond restoring terminal behavior.
- **Proposed resolution**: Defer `design_pause.py` helper integration and `test_design_pause.py` additions; keep the shared helper plus `design_publish.py`, `clarify.py`, and Step 5c delegation as the minimum fix for the reported regression.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_pause.py:219-238
- **Concern**: [SCOPE-REDUCTION] Pause snapshot final-summary rendering exceeds the binding bug scope. Scenario: The issue is terminal `/design` final-report output and tracking-comment upsert. Pause is a non-terminal checkpoint; adding pause outcome, upsert suppression, and pause-specific tests expands the fix without restoring the reported regression
- **Proposed resolution**: Drop `design_pause.py` helper wiring, the new pause outcome token, and `test_design_pause.py` additions from this change. Limit pre-log-publish rendering to terminal callers (`publish_core`, clarify publish)

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:141-143
- **Concern**: [SCOPE-REDUCTION] Testing strategy asks for full `make py-test` and `make py-lint`, which conflicts with the repo constraint to lint/test only changed files.. Scenario: The plan expands validation beyond the minimum-change contract, while CI owns the full sweep.
- **Proposed resolution**: Drop the full-sweep commands. Keep the listed focused pytest files and changed-file lint only.
