### FINDING_1: Update the tier-A backfill fixture to a genuine failure trigger
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan omits updating `test_failure_report_escalation_tier_a_backfill_failures_are_specific`, which still seeds a normal main-agent handoff trigger. Once the gate only counts genuine Step-3 failures, that test will skip the escalation-success path instead of exercising the tier-A fallback-print branches it asserts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change that fixture trigger to tally-error or panel-failed like test_failure_report_escalation_success_from_ledger or add an explicit plan step to update every failure_report_escalation test that seeds design-failure-escalation-ledger.tsv
  - From Codex-Arch: Change the seeded trigger to tally-error or panel-failed, or split out a dedicated genuine-failure fixture for this test.
  - From Cursor-Innovation: Add test_failure_report_escalation_tier_a_backfill_failures_are_specific to the test_design_lifecycle.py changes: switch its ledger trigger to tally-error or panel-failed (same as the updated success-from-ledger test), or add a separate parametrized normal-only skip case if you split concerns.
  - From Cursor-Pragmatic: Also retarget that test’s ledger to a genuine-failure trigger (e.g. `tally-error` or `panel-failed`), matching the `test_failure_report_escalation_success_from_ledger` update.
  - From Cursor-Requirements: Add this test to the python/tests/design/test_design_lifecycle.py section: change its ledger fixture to a genuine-failure trigger (tally-error or panel-failed), matching the planned change to test_failure_report_escalation_success_from_ledger.


### FINDING_2: Add mixed-ledger coverage and ensure the helper scans every row
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-Design Escalation Gate
- **Severity**: important
- **Concern**: The plan needs to prove that the gate treats any ledger/fallback row with a genuine-failure trigger as evidence. Without mixed-row and malformed/no-trigger coverage, an implementation that only inspects the first row or that treats any non-empty ledger as evidence could still pass the planned tests and misclassify legacy ledgers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify in design_terminal helper that it iterates all ledger and fallback lines and returns true when any parsed trigger is in STEP3_ESCALATION_FAILURE_STATUSES; add a mixed-row lifecycle test (normal row then tally-error)
  - From Cursor-Pragmatic: Add a `test_design_lifecycle.py` case with two ledger rows (normal handoff then genuine failure) asserting `DESIGN_FAILURE_REPORT_DECISION=escalation-success`, and implement the helper to scan every row in ledger and fallback files.
  - From Codex-Requirements: Add a ledger parameterized case that mixes a normal handoff row with a genuine-failure row, and a malformed/no-trigger case that must skip with DESIGN_FAILURE_REPORT_REASON=no-escalation-evidence.
  - From Cursor-dyn-Design Escalation Gate: State explicitly in the design_terminal.py change that the helper scans every ledger and fallback row and returns true on the first trigger in STEP3_ESCALATION_FAILURE_STATUSES


### FINDING_1: Step 3 harness still assumes normal handoffs record escalation rows
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The plan leaves `skills/design/scripts/test-design-step3-review.sh` expecting escalation rows for the normal handoff statuses, so `make test-design-step3-review` would still fail once `step3_record_report_evidence` stops recording evidence for `main-agent-vote-required`, `main-agent-apply-required`, and `postplan-operator-required`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add this harness to the plan. Keep recorded-evidence assertions only for the four genuine failures, and add no-record assertions for the three normal handoffs.
  - From Codex-Requirements: Add `### UPDATED: skills/design/scripts/test-design-step3-review.sh` to split genuine-failure statuses from normal handoffs, assert no ledger/fallback/marker for normal handoffs, and add `make test-design-step3-review` to the testing strategy.


### FINDING_2: Step 3 allowlist would suppress validator-autofix escalation evidence
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: A Step 3-only evidence gate would drop existing validator-autofix escalation rows, so approved runs after validator escalations could skip with `no-escalation-evidence` instead of filing the current escalation-success report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Filter only step3-review rows by the new Step 3 allowlist. Keep other parseable design escalation rows as evidence, or add a small separate allowlist for existing validator-autofix triggers. Add one targeted lifecycle test with a validator-autofix ledger row.

