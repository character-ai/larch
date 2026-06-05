### FINDING_1: mav-resume-past-cap can overwrite already-recorded deferred MAV timing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-handoff-output.txt
- **Severity**: important
- **Concern**: `mav-resume-past-cap` re-records deferred round timing when `round-start-s` still exists after the MAV/coder handoff already emitted a ledger row. The replacement can inflate `end_s`/duration and cause the round to disappear from `timing-report.json` when it no longer fits the Step 5 interval. Coverage for preventing this overwrite is also missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-handoff-output.txt: Address the concern above.


### FINDING_10: Plan MAV artifact tests do not prove round-start-s survives snapshot pruning
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Current coverage checks allowlist inclusion and `round-start-s` creation but not survival through snapshot pruning, so deferred MAV timing could break while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Plan OOS tally parsing lacks exonerated-row coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: OOS tally parsing tests omit exonerated OOS rows, so future parsing changes could count exonerated or rejected OOS rows and inflate design timing metrics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Round rows ending after a parent step interval silently disappear from JSON
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `timing-report.sh` only attaches rounds when `round_end <= step_end`. Deferred rows recorded slightly after the step boundary remain in the ledger but vanish from rendered JSON, and coverage for this boundary behavior is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Terminal plan-review statuses lack round-timing assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Several terminal plan-review paths using `_snapshot_terminal_exit_preserving_status` lack assertions that a timing ledger row is emitted, including cap-hit snapshot-failed and other edge exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: Deferred timing helpers can delete the only round row before failed append
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Implement and design helpers delete an existing round row before appending the replacement. If append fails under flock contention, the only row can vanish from the ledger without a rendered execution-issues warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Design round counts are sourced from session-root artifacts instead of snapshots
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` reads counts from session-root artifacts. After clearing or reordering, it can record wrong counts for a round whose snapshot still has correct data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: Orchestrator stall deferred timing lacks end-to-end coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Stall deferred timing is documented but not integration-tested end to end; existing tests call the helper directly and would miss wrapper/resume regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: Handoff fence can commit/reinvoke during terminal stall
- **Reviewer(s)**: dyn-handoff-output.txt
- **Severity**: important
- **Concern**: The handoff bash fence mechanically runs `git add -A` and commit/reinvoke after timing emission, while prose says terminal lint/check stalls should emit timing and skip commit/reinvoke. An orchestrator executing the full fence during a stall could advance the tree incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-output.txt: Address the concern above.


### FINDING_23: mktemp failure cleanup removes the failure sidecar
- **Reviewer(s)**: dyn-publish-artifacts-output.txt
- **Severity**: important
- **Concern**: On `mktemp` failure, the publish timing render writes `timing-report-final.failure.log` and then deletes it with the cleanup glob, removing diagnostics operators would inspect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-artifacts-output.txt: Address the concern above.


### FINDING_24: Pre-publish timing JSON validation only checks syntax
- **Reviewer(s)**: dyn-publish-artifacts-output.txt
- **Severity**: important
- **Concern**: `jq -e .` accepts any valid JSON, not necessarily a timing-report shape with `per_step`, Step 3, or `rounds`, so malformed or partial timing output could be committed as validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-artifacts-output.txt: Address the concern above.

### FINDING_7: Generic stall branch can also overwrite an existing deferred timing row
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The generic stall branch re-emits timing whenever `round-start-s` exists, using the same replacement semantics as `mav-resume-past-cap`. Future stall paths could overwrite correct rows and lose JSON attachment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


