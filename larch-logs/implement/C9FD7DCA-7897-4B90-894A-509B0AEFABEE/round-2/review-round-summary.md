# Review Round 2

- Mode: `diff`
- 4 accepted, 27 rejected (15 neutral)

## Accepted Findings

### FINDING_11: Dispatch failures can abort before terminal audit flush
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Dispatch/waterfall failures can exit under `set -e` before panel-failed flush and snapshot logic writes required audit records such as prune and round-summary env files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Fluff-analysis live corpus smoke thresholds are stale
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The corpus smoke test asserts thresholds that the current committed corpus does not satisfy, so CI can fail despite analyzer output matching the branch’s present corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: MAV ledger test contradicts expected B2 behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The MAV ledger test does not assert the expected launched-slot ledger rows and may either fail a healthy implementation or miss accidental removal of MAV ledger recording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_32: ns-retry sidecar presence without meta can pass audits
- **Reviewer(s)**: dyn-signal-migration-correctness-output.txt
- **Severity**: important
- **Concern**: The migrated ns-retry scan counts non-empty `reviewer_signals.ns_retry_reason`; a retry sidecar with missing or unreadable meta can produce an empty reason and pass despite old file-glob semantics failing it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-signal-migration-correctness-output.txt: Address the concern above.


