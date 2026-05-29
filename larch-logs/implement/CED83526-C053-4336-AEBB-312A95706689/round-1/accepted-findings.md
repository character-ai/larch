### FINDING_1: Claude assessor failure skips tally despite usable external outputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Claude-only assessor failure sets `DISPATCH_OK=false`, causing `assess-plan-round.sh` to skip tally even when Codex/Cursor produced parseable votes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: New test harnesses lack markdown contract siblings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Five new `test-*.sh` harnesses lack required `test-*.md` siblings, drifting from the repository’s script documentation convention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


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


### FINDING_2: Degraded dispatch points to missing verdict env file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Dispatch-failure degraded path emits empty `ASSESSOR_VERDICT_ENV` while Step 3.6 tells operators to inspect a verdict `.env` that was never written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: feature-description.txt is missing from snapshot preflight
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` does not preflight `feature-description.txt`, so missing feature context fails later as a generic dispatch problem.
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


### FINDING_29: WORSE-majority qualification fallback can deny the actual verdict
- **Reviewer(s)**: dyn-tally-distribution-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` uses the same “no WORSE-majority consensus” fallback even when `worse_majority=true` and no WORSE assessor supplied qualifications.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tally-distribution-output.txt: Address the concern above.


### FINDING_3: QUALIFICATIONS_SUMMARY drops distinct WORSE qualifications
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `QUALIFICATIONS_SUMMARY` uses only the first WORSE assessor qualification instead of synthesizing or joining multiple WORSE qualifications.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


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


### FINDING_5: assess-plan-round harness misses degraded and snapshot-warning paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-assess-plan-round.sh` does not cover missing snapshots, append-tool failure warnings, TRIVIAL skip, degraded-default-open dispatch failure, or stale-file removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: dispatch-plan-assessors harness covers only happy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-plan-assessors.sh` omits narration-only Cursor output, degraded panel behavior, launcher failure, and KV/breadcrumb assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


