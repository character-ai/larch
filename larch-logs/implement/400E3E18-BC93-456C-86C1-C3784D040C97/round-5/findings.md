### FINDING_1: mav-resume-past-cap can overwrite already-recorded deferred MAV timing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-handoff-output.txt
- **Severity**: important
- **Concern**: `mav-resume-past-cap` re-records deferred round timing when `round-start-s` still exists after the MAV/coder handoff already emitted a ledger row. The replacement can inflate `end_s`/duration and cause the round to disappear from `timing-report.json` when it no longer fits the Step 5 interval. Coverage for preventing this overwrite is also missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-handoff-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Publish and pause timing render helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-publish-artifacts-output.txt
- **Severity**: important
- **Concern**: Publish and pause paths have near-duplicate timing render helpers. Fixes to cleanup, validation, stale sidecars, or env hygiene can diverge, and pause-path failure/quarantine coverage is weaker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-publish-artifacts-output.txt: Address the concern above.

### FINDING_3: Implement/design timing helpers duplicate ledger replacement logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The implement and design record helpers duplicate ledger deduplication and post-write verification logic, so replace-by-round behavior can diverge between code paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: timing-report round ordering uses unnecessary O(n²) sort
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `emit_round_array` uses bubble sort for round ordering. It is harmless at current caps but unnecessarily complex in the JSON hot path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Step 5 loop duplicates timing ledger verification
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_emit_implement_round_timing_row` repeats verification already performed by `record-implement-review-round-timing.sh`, adding extra scans and another place for guard semantics to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] render-final-summary timing rerender can diverge from published artifacts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-artifacts-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` still performs its own timing rerender after publish, with different temp/stderr behavior and potential mismatch from already-published timing artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-artifacts-output.txt: Address the concern above.

### FINDING_7: Generic stall branch can also overwrite an existing deferred timing row
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The generic stall branch re-emits timing whenever `round-start-s` exists, using the same replacement semantics as `mav-resume-past-cap`. Future stall paths could overwrite correct rows and lose JSON attachment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Implement tally env parsing can skip partially populated counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The tally env reread is all-or-nothing. If only `ACCEPTED_COUNT` is present, `REJECTED_COUNT` can remain empty and produce wrong round-row counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Pause/resume timing test uses weak/non-canonical fixture validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Pause/resume timing tests use a non-canonical design step label and do not validate rendered round content strongly enough, so wrong labels or empty renders could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

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

### FINDING_16: Plan-review degraded-empty and zero-finding branches could double emit after refactor
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Sequential `if` blocks for degraded-empty-collector and converged zero-findings paths rely on `_terminal_exit`; a refactor could allow double snapshot/emission with conflicting statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] General ledger appends can fail closed under flock contention
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing flock fail-closed behavior can drop unrelated ledger rows under contention, not just deferred round timing rows.
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

### FINDING_20: [OUT_OF_SCOPE] mav-resume-past-cap resume envelope reports ROUNDS_COMPLETED=0
- **Reviewer(s)**: dyn-handoff-output.txt
- **Severity**: nit
- **Concern**: Entry-time `mav-resume-past-cap` sets `ROUNDS_COMPLETED=0` even when resuming after real rounds, causing telemetry-only skew.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] No additional deferred-handoff gaps identified
- **Reviewer(s)**: dyn-handoff-output.txt
- **Severity**: nit
- **Concern**: Reviewer reported no other pre-existing deferred-handoff gaps beyond the in-scope handoff findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-handoff-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Pre-publish timing render failure can still allow committed logs without timing JSON
- **Reviewer(s)**: dyn-publish-artifacts-output.txt
- **Severity**: important
- **Concern**: If pre-publish timing render or validation fails, publish can still proceed without staging `timing-report-final.json`; post-publish summary may later render fresh timing only in tmpdir, leaving committed logs permanently missing per-round timing. Related test coverage does not fully assert the warning/no-artifact path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-artifacts-output.txt: Address the concern above.

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
