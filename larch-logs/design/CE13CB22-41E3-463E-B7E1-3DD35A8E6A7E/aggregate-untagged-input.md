### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_terminal.py:504-512
- **Concern**: The row-evidence helper treats a missing or empty site= as non-step3-review evidence, which conflicts with the plan edge case that malformed rows without parseable site=/trigger= must not count.. Scenario: A legacy or corrupt ledger/fallback row with trigger=main-agent-apply-required (or another normal handoff) but no site= field satisfies site != step3-review and still makes escalation_evidence_present() true on an approved run, so escalation-success can still be filed after ledger filtering is otherwise correct.
- **Proposed resolution**: Require parseable site= and trigger= before a row can qualify; then count rows only when site is present and not step3-review, or when site=step3-review and trigger is in STEP3_ESCALATION_FAILURE_STATUSES. Add a missing-site ledger/fallback negative test alongside the planned malformed/no-trigger case.

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:57-59
- **Concern**: Runtime Step 3 contract is left stale after handoff evidence is removed. Scenario: The mandatory Step 3 reference will still say `design-step3-review.sh` owns `record-escalation` for `main-agent-vote-required`, `main-agent-apply-required`, and `postplan-operator-required`, even though the plan makes those statuses no-op evidence paths. That leaves a shipped prompt-side contract pointing back at the bug class.
- **Proposed resolution**: Add this file to the firm updates and change the sentence to say only genuine Step 3 failures record escalation evidence; normal handoffs are routing-only and prompt-side orchestration still must not call `record-escalation` manually.
