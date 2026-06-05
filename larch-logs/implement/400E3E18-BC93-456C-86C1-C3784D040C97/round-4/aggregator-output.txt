### FINDING_1: Duplicated timing-report-final render/quarantine logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Pause-save and design-publish duplicate timing-report-final.json render/quarantine logic, making stale sidecar handling or jq validation fixes easy to miss in one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Implement round timing writers have inconsistent count/idempotency behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Implement in-loop and deferred round timing paths use different writers/count sources and brittle idempotency policies, allowing duplicates, stale bad rows, skipped corrections, or last-writer ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Implement loop timing emit callsites are duplicated and under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_emit_implement_round_timing_row` is copied across many loop branches, while the loop-timing harness does not drive `run_implement_loop`, so missed emissions on continuation/stall paths could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Deferred round timing helpers duplicate common plumbing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Implement and plan deferred helpers duplicate argv parsing, tmpdir canonicalization, ledger binding, and idempotency code, increasing maintenance risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Timing render failures use inconsistent issue categories
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pause-save logs timing render failures as Tool Failures while design-publish logs them as Warnings, creating inconsistent operator audit output for the same failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Implement handoff timing can be recorded after Step 7 or remain prompt-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-handoff-state-output.txt
- **Severity**: important
- **Concern**: MAV/coder/stall handoff timing relies on prompt ordering and merged record/commit/resume fences; late fallback emits after Step 7 can inflate Step 5 duration, and missing mechanical tests/guards allow regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-handoff-state-output.txt: Address the concern above.

### FINDING_7: Final summary can freeze stale timing totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` can skip timing regather when `timing-report-final.json` already exists, leaving later Step 6 cleanup marks out of published final timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Handoff record-before-commit remains prompt-enforced
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Implement handoff ordering can omit `record-implement-review-round-timing.sh` before commit without a script-level failure, leaving round rows missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Design MAV deferred timing can be lost on tally-error and lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-handoff-state-output.txt
- **Severity**: important
- **Concern**: Design MAV deferred timing is emitted only after successful re-tally; a tally-error short-circuit can skip `record-plan-review-round-timing.sh`, and tests do not cover this handoff path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-handoff-state-output.txt: Address the concern above.

### FINDING_10: Summary/terse timing-report modes lack round-row regression tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tests verify markdown with round rows but not `--summary` or `--terse`, so rounds could leak into those modes unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: review-summary.json rejected fallback is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The rejected-count fallback from `review-summary.json` is not tested when `review-tally.env` is missing or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Pause/resume timing tests use weak/noncanonical fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pause/resume tests use noncanonical Step 3 labels and weak assertions, which could hide future round attachment bugs in pause publish coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Design deferred timing helper lacks tmpdir allowlist validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `record-plan-review-round-timing.sh` accepts a canonicalized design tmpdir without validating it against allowed session roots before ledger I/O and artifact reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Implement deferred timing helper lacks tmpdir allowlist validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `record-implement-review-round-timing.sh` accepts any non-symlink implement tmpdir before binding ledger paths and reading round artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Broader implement tmpdir validation surface remains unguarded
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Other scripts accepting `--implement-tmpdir`, including `run-step5-review.sh`, share the same latent write/read surface without root allowlist validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Timing report attaches rounds without bounding round end/duration
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-telemetry-ledger-output.txt
- **Severity**: important
- **Concern**: `timing-report.sh` attaches round rows by start time only, so rows ending after the parent step can publish inflated durations that span later steps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-telemetry-ledger-output.txt: Address the concern above.

### FINDING_17: Invalid or missing implement round-start can silently drop deferred timing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-handoff-state-output.txt
- **Severity**: latent
- **Concern**: Implement round-start persistence/read paths do not consistently validate or populate numeric `round_start_s`; helper validation failures can be swallowed, omitting deferred round timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-handoff-state-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Pause mktemp failure log is deleted immediately
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `design-pause-save.sh` writes `timing-report-final.failure.log` on mktemp failure and then deletes it, reducing operator inspectability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: run-logs docs omit new timing-report rounds schema
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `docs/run-logs.md` does not document the additive `rounds` arrays, fields, and attachment rules for committed `timing-report.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: Design plan loop marks timing emitted without verifying ledger row
- **Reviewer(s)**: dyn-telemetry-ledger-output.txt
- **Severity**: latent
- **Concern**: `_emit_plan_round_timing_row` can set the per-round emitted guard after a best-effort helper exit even if no ledger row landed, preventing later retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-telemetry-ledger-output.txt: Address the concern above.

### FINDING_21: Duplicate timing-report round rows are collapsed silently
- **Reviewer(s)**: dyn-telemetry-ledger-output.txt
- **Severity**: latent
- **Concern**: `emit_round_array` silently keeps one row when duplicate `(skill, step, round)` rows match a step interval, hiding production double-writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-telemetry-ledger-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] timing-ledger record-round failures still exit 0
- **Reviewer(s)**: dyn-telemetry-ledger-output.txt
- **Severity**: latent
- **Concern**: `timing-ledger.sh` forces exit 0 even when `record-round` fails, so callers need ledger scraping to detect validation or append failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-telemetry-ledger-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Implement helper round-number idempotency blocks later correction
- **Reviewer(s)**: dyn-telemetry-ledger-output.txt
- **Severity**: latent
- **Concern**: `record-implement-review-round-timing.sh` dedupes only by `(skill, step, round)`, so a malformed first row can prevent a later corrected row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-telemetry-ledger-output.txt: Address the concern above.
