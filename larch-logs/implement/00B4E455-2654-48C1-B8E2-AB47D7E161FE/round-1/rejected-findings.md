### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Final summary launcher lacks rejoin guards
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Final-summary bgjob launches can be retried without the rejoin/idempotency protections used in neighboring steps, so a duplicate start can clobber shared sentinel/merge-env state and drop `FINAL_SUMMARY_PATH` even when `BGJOB_RC=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Brainstorm lanes bypass lane-scoped rejoin
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: The brainstorm framing/scope lanes still launch bgjobs directly instead of using per-lane rejoin and merge-env recreation, so restarted lanes can collide on registry state or overwrite external output before collection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Final-summary lifecycle tests miss result-env coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Final-summary lifecycle coverage still misses the bgjob start/wait integration check and the success-path/stale-env assertions for `FINAL_SUMMARY_PATH` and the merge-result env, so regressions could slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add bgjob start/wait integration test asserting BGJOB_RC=0 and FINAL_SUMMARY_PATH in bgjob result env.
  - From cursor-specialist-testing: Assert .design-step-final-summary-result.env contains FINAL_SUMMARY_PATH before the terminal sentinel on success paths.
  - From cursor-specialist-testing: Add a lifecycle test that seeds a stale env and verifies unlink/rewrite on the next successful run.
  - From codex-specialist-testing: Add a regression test that seeds stale merge-result contents, runs `step_final_summary_core` on a fresh tempdir, and asserts the stale value is cleared before completion.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Symlinked merge-env parents are rejected
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `design_write_merge_env` rejects symlinked parent directories, so permitted sessions rooted through a symlinked `DESIGN_TMPDIR` can fail on merge-env writes even when the resolved path stays inside the allowed tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Brainstorm harness lacks bgjob contract pins
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: The brainstorm prompt-shape harness still lacks the migrated bgjob contract pins, so regressions to a shared step slug, missing merge-env truncation, missing wait gating, or reintroduced `run_in_background` would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add BRAINSTORM_MD contains/not_contains rows for bgjob start, design-brainstorm-framing/scope slugs, per-lane merge-env truncation, and no run_in_background.
  - From cursor-specialist-testing: Add contains/not_contains pins for design-brainstorm-framing/scope, per-lane merge-result-env truncation, bgjob wait gating, and no run_in_background in brainstorm.md.
  - From cursor-specialist-plan-fidelity-auto: Add brainstorm contains/not_contains pins for per-lane step slugs, merge-env truncation, bgjob wait, and BGJOB_RC=0 gating.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Empty final-summary still emits only the sentinel
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: When `final-summary.md` is empty or missing, the step still writes the compatibility sentinel while omitting `FINAL_SUMMARY_PATH` from the merge env, so completion signals diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Stale final-summary result env survives fresh launch
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Fresh-start cleanup leaves the canonical bgjob result env behind, so a stale `.design-step-final-summary-result.env` can make `bgjob wait` return DONE immediately and can feed old `FINAL_SUMMARY_PATH` data back into retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: SKILL.md still uses immediate-background guidance
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: `skills/design/SKILL.md` still describes Final summary and Step 5c with immediate-background breadcrumb wording, and its global anti-halt language still points migrated helpers at the old wait model instead of the bgjob contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

