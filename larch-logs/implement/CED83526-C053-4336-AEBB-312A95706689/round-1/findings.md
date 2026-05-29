### FINDING_1: Claude assessor failure skips tally despite usable external outputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Claude-only assessor failure sets `DISPATCH_OK=false`, causing `assess-plan-round.sh` to skip tally even when Codex/Cursor produced parseable votes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Degraded dispatch points to missing verdict env file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Dispatch-failure degraded path emits empty `ASSESSOR_VERDICT_ENV` while Step 3.6 tells operators to inspect a verdict `.env` that was never written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: QUALIFICATIONS_SUMMARY drops distinct WORSE qualifications
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` uses only the first WORSE assessor qualification instead of synthesizing or joining multiple WORSE qualifications.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: Write-once round snapshots can become stale on same-round re-entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `plan-after-round-N` is write-once, so re-running Step 3.6 for the same round after `plan.txt` changed can compare against an outdated snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: assess-plan-round harness misses degraded and snapshot-warning paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-assess-plan-round.sh` does not cover missing snapshots, append-tool failure warnings, TRIVIAL skip, degraded-default-open dispatch failure, or stale-file removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Timing allowlist omits assessor task kinds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-timing-kinds.sh` lacks assessor task-kind entries, so current or future assessor launcher timing records can trip unknown-kind validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: dispatch-plan-assessors harness covers only happy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-plan-assessors.sh` omits narration-only Cursor output, degraded panel behavior, launcher failure, and KV/breadcrumb assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] snapshot-plan-round harness lacks write-once and interrupt coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cursor-ordering-output.txt
- **Severity**: important
- **Concern**: Snapshot tests do not exercise second write-after preservation or atomic rename / interrupt failure paths called out by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-cursor-ordering-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] tally distribution table is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-tally-distribution-output.txt
- **Severity**: important
- **Concern**: `test-tally-plan-assessor.sh` lacks regression rows for documented tie-heavy and partial-success tuples such as `(2,1,0)`, `(0,3,0)`, and `(0,2,0)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-tally-distribution-output.txt: Address the concern above.

### FINDING_10: New test harnesses lack markdown contract siblings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Five new `test-*.sh` harnesses lack required `test-*.md` siblings, drifting from the repository’s script documentation convention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] structure tests do not pin Gate B to Step 3.6 routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-skill-gate-coverage-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` does not assert that Gate B settled paths forward through Step 3.6, so routing regressions would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] no integration coverage for Step 3 cursor and round-2 assessor flow
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cursor-ordering-output.txt
- **Severity**: latent
- **Concern**: No integration fixture exercises Step 3 cursor advancement, Gate B, Step 3.6 write-after, and second Step 3 entry together.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-cursor-ordering-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] passive-summary Gate B path can skip Step 3.6
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-skill-gate-coverage-output.txt
- **Severity**: important
- **Concern**: Passive-summary Gate B routing can send HARD converged/cap-hit runs toward Gate C without Step 3.6, write-after, or assessor execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.

### FINDING_14: Assessor prompts disclose unredacted plan and issue content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render-assessor-prompt.sh` sends inlined plans and feature text to external assessors without pre-dispatch redaction of secrets or temporary paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: External assessor text is surfaced without untrusted-content framing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: External `QUALIFICATIONS` / `REASONING` can flow into operator prompts without labeling, fencing, sanitization, or newline normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: dispatch-plan-assessors accepts unsafe round numbers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--round-num` is used in filesystem paths without validation, allowing direct invocations with slashes to write under unintended subdirectories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: Tally failure is not contained as degraded-default-open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `tally-plan-assessor.sh` runs under `set -e`; argv, unreadable output, or disk errors can abort Step 3.6 instead of emitting the fail-open KV contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: WORSE-majority UX is not bound to fresh HARD assessor state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Continue/Stop prompt can fire outside the HARD-only path or from stale `ASSESSOR_VERDICT` state after a later skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: write-after failure is ignored before assessment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 does not check `write-after` exit status before running assessment, so missing snapshots can lead to inconsistent comparisons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: feature-description.txt is missing from snapshot preflight
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` does not preflight `feature-description.txt`, so missing feature context fails later as a generic dispatch problem.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Multiple ASSESSMENT lines use last verdict
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `parse_assessment` uses the last `ASSESSMENT:` line, so preamble or revised verdicts can change tally behavior unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Step 3 short-circuit statuses bypass Step 3.6
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `panel-failed`, `tally-error`, and `cap-reached` Step 3 exits can bypass Gate B and Step 3.6, leaving assessor behavior undefined on those paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Step 3 does not check write-cursor before using incremented ROUND_NUM
- **Reviewer(s)**: dyn-cursor-ordering-output.txt
- **Severity**: important
- **Concern**: Step 3 advances in-shell `ROUND_NUM` and calls `plan-review-loop.sh` without verifying `write-cursor` succeeded, allowing cursor file and shell state to diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-ordering-output.txt: Address the concern above.

### FINDING_24: Cursor parsing allows leading-zero values that break arithmetic
- **Reviewer(s)**: dyn-cursor-ordering-output.txt
- **Severity**: important
- **Concern**: `parse_cursor_file` accepts values like `008`, but later Bash arithmetic lacks a `10#` prefix and can abort cursor advancement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-ordering-output.txt: Address the concern above.

### FINDING_25: Step 3.6 can use stale ROUND_NUM instead of cursor file
- **Reviewer(s)**: dyn-cursor-ordering-output.txt, dyn-skill-gate-coverage-output.txt
- **Severity**: important
- **Concern**: Step 3.6 only re-reads the cursor when `ROUND_NUM` is empty, so leaked or stale shell state can write snapshots for the wrong round while assessment reads the cursor independently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cursor-ordering-output.txt: Address the concern above.
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.

### FINDING_26: Assessor background writer does not publish paired PID
- **Reviewer(s)**: dyn-background-monitor-pair-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-assessors.sh` does not call `larch_quiet_write_paired_pid_file`, so `breadcrumb-monitor.sh` cannot terminate the long-running assessor dispatch tree on timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-background-monitor-pair-output.txt: Address the concern above.

### FINDING_27: LARCH_QUIET_DISABLE suppresses assessor breadcrumbs
- **Reviewer(s)**: dyn-background-monitor-pair-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` launches dispatch with `LARCH_QUIET_DISABLE=1` while a breadcrumb stream is exported, making `emit_breadcrumb` a no-op during the panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-background-monitor-pair-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] paired-PID timeout behavior is not tested
- **Reviewer(s)**: dyn-background-monitor-pair-output.txt
- **Severity**: latent
- **Concern**: The assessor harness stubs `breadcrumb-monitor.sh` to exit 0, so CI does not exercise paired-PID timeout behavior or catch missing paired-PID writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-background-monitor-pair-output.txt: Address the concern above.

### FINDING_29: WORSE-majority qualification fallback can deny the actual verdict
- **Reviewer(s)**: dyn-tally-distribution-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` uses the same “no WORSE-majority consensus” fallback even when `worse_majority=true` and no WORSE assessor supplied qualifications.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-distribution-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] REASONING and QUALIFICATIONS labels are case-sensitive
- **Reviewer(s)**: dyn-tally-distribution-output.txt
- **Severity**: latent
- **Concern**: Only `ASSESSMENT:` is matched case-insensitively; atypical casing for `REASONING:` or `QUALIFICATIONS:` can drop structured fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-distribution-output.txt: Address the concern above.

### FINDING_31: Step 3.5 prose can skip Step 3.6 on zero-findings paths
- **Reviewer(s)**: dyn-skill-gate-coverage-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` says Step 3.6 follows Gate B only after Step 2b.5 returns, but zero-findings routes do not go through Step 2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.

### FINDING_32: zero-findings-degraded-panel matrix bypasses Step 3.6
- **Reviewer(s)**: dyn-skill-gate-coverage-output.txt
- **Severity**: important
- **Concern**: The Step 3 post-loop matrix routes `LOOP_STATUS=zero-findings-degraded-panel` directly to Step 3b, conflicting with Gate B text that routes zero-findings through Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.

### FINDING_33: Gate C path enumeration omits Step 3.6
- **Reviewer(s)**: dyn-skill-gate-coverage-output.txt
- **Severity**: important
- **Concern**: Gate C’s “When” section still lists settled paths as going to Step 3b / Step 4 / Step 4b without Step 3.6, contradicting updated zero-findings routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] plan-review reference still routes zero-findings straight to Step 3b
- **Reviewer(s)**: dyn-skill-gate-coverage-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/plan-review.md` still says the zero-findings short-circuit passes straight through to Step 3b, creating pre-existing routing drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-gate-coverage-output.txt: Address the concern above.
