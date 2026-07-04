# Review Round 1

- Mode: `diff`
- 7 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 5 terminal envelope handling
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: A replayed valid Step 5 terminal envelope can still be treated as non-terminal, so the wrapper may skip `.completed/step-5-terminal` and the SKILL carve-out can re-enter Step 5 even though `STEP5_REVIEW_STATUS` was already replayed from stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Gate carve-out on missing STEP5_REVIEW_STATUS in stdout or clear detached marker when emitting terminal stall from reattach failure
  - From codex-specialist-correctness: Make normalization success mean “a Step 5 envelope was replayed”; write `.completed/step-5-terminal` for any replayed envelope, then preserve the desired process exit separately, or change `normalize-status` to return non-zero only when the envelope is absent.
  - From codex-specialist-edge-cases: Write the terminal sentinel when a valid Step 5 envelope is normalized, independent of the loop rc, then return the original loop rc.
  - From codex-specialist-testing: Write the sentinel when normalization validates an envelope, and preserve child rc separately.


### FINDING_3: Step 5 harness coverage gaps
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: The Step 5 shell harness still stubs out the plan-required reattach, pre-identity TERM, and stale-marker/no-duplicate-launch cases, so CI can stay green while detached-marker reentry and signal-order regressions are untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Implement reattach/pre-identity tests from the plan
  - From cursor-specialist-edge-cases: Add pre-identity TERM, reattach, and stale-marker tests; remove no-op pass
  - From cursor-specialist-testing: Implement reattach and no-duplicate-launch cases that assert await-loop-identity, normalize-status, and a single step5 launch.
  - From cursor-specialist-testing: Add STEP5_STUB_DELAY_IDENTITY case; TERM wrapper early; assert no detached or terminal markers and child group exits.
  - From codex-specialist-testing: Add deterministic harness cases for delayed identity signal cleanup and detached-marker reentry without fresh loop launch.


### FINDING_4: Detached-marker orphan timeout must use the stored detach epoch
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-signal-lifecycle
- **Severity**: important
- **Concern**: Orphan-timeout age is computed from marker mtime, so any rewrite or restore of `.step5-wrapper-detached` can reset the 7200s bound even though the original detach happened earlier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Parse DETACHED_AT_EPOCH from marker content for age checks
  - From cursor-specialist-edge-cases: Read DETACHED_AT_EPOCH from marker KV; preserve original epoch on marker restore
  - From dyn-dyn-signal-lifecycle: On normalize failure, either stop restoring the detached marker (or restore without bumping detach time by parsing `DETACHED_AT_EPOCH`), and/or treat normalize-fail reattach as a terminal stall with `STEP5_REVIEW_STATUS=stall` instead of routing through the detached-marker re-invoke carve-out; have orphan checks use `DETACHED_AT_EPOCH` so retries cannot reset the bound.
  - From dyn-dyn-signal-lifecycle: Parse `DETACHED_AT_EPOCH` from the marker (fail closed if missing on a detached marker) and compute `time.time() - detached_at`; only fall back to mtime when the field is absent for backward compatibility.


### FINDING_5: Step 3 orphan-timeout normalization must preserve the orphan route
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: Dropping `REASON=orphan-timeout` lets the zero-coverage fallback rewrite a planned orphan timeout into `panel-init-failed` instead of preserving `panel-failed` and `NEXT_ACTION=step3b-bypass`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add REASON to the normalize allow/read/emit sets and special-case `REASON=orphan-timeout` before the zero-coverage conversion so it keeps `panel-failed`, `LOOP_STATUS=panel-failed`, and `NEXT_ACTION=step3b-bypass`.


### FINDING_6: Wrapper stall envelopes should keep STALL_TRACKING true
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Terminal wrapper failures emit a stall envelope with `STALL_TRACKING=false`, which can make later tracking or rename logic treat a real stall as non-stallable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Use STALL_TRACKING=true for terminal wrapper stall reasons


### FINDING_8: Step 5 setsid fail-closed coverage is missing
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: Step 5 does not yet exercise the `setsid` unavailable or `OSError` fail-closed paths required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Mirror test_plan_review.py new-process-group OSError/unavailable tests for review_and_fix.step5.


### FINDING_9: Step 3 orphan-timeout integration coverage is missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The aged detached-marker path through plan-review is not exercised end-to-end, so the normalize-to-step3b-bypass route can drift unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add pytest driving aged detached marker through plan-review run and normalize to step3b-bypass.


