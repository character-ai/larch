### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `ROUND_NUM` is no longer propagated to the Step 3 fence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Main-agent vote paths can see empty `ROUND_NUM`, causing downstream paths such as `round-/findings-classification.tsv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Multi-round integration bypasses `run-step3-review.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Full multi-round integration does not exercise the new wrapper, so wrapper regressions in cap, cursor, or persistence behavior rely only on narrower harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `CLAUDE_PLUGIN_ROOT` precedence lacks unit coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-parity-output.txt
- **Severity**: nit
- **Concern**: `phase_driver_resolve_plugin_root` documents env-var precedence over session env and tree walk, but the harness does not assert that branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-harness-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_18: Final result-env write return value is unchecked
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` can exit successfully even if `phase_driver_write_result_env` fails, allowing the orchestrator to read stale normalized state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_19: Cap-reached path skips round forensics cleanup
- **Reviewer(s)**: dyn-round-state-output.txt
- **Severity**: important
- **Concern**: When cap is reached at entry, stale `plan-review/round-*` artifacts are not cleaned even though the old flow cleared them on every Step 3 entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-round-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_20: Operator-facing diagnostics use the contract stream after quiet init
- **Reviewer(s)**: dyn-quiet-io-output.txt
- **Severity**: latent
- **Concern**: Human warnings and breadcrumbs in `run-step3-review.sh` are emitted through `emit`/FD 3 after `larch_quiet_init`, mixing diagnostics with machine KVs and making them easy to capture or lose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-io-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: Inner-loop `WARN` lines can disappear from Step 3 chat surface
- **Reviewer(s)**: dyn-quiet-io-output.txt
- **Severity**: latent
- **Concern**: `WARN=` lines are republished with `emit_kv WARN`, but the new fence does not read `WARN` from the normalized env or `_plan_review_out`, so panel warnings may not be surfaced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-io-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Step 3 driver duplicates result-env parsing instead of using shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run-step3-review.sh` reimplements allowlisted result-env parsing instead of exercising `phase_driver_read_result_env`, increasing drift risk for this and future extracted phase drivers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Redundant cap-env re-source creates dead cap branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` re-sources `.step3-review-cap.env` and checks `STEP3_REVIEW_CAP_REACHED` again after the outer cap guard, leaving confusing dead control flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Unused `_allow` array remains in Step 3 driver
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` declares `_allow` but never reads it, which can mislead maintainers and may fail stricter future shell linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Cap env persistence uses inconsistent non-atomic primitive
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `.step3-review-cap.env` is written with `cat >` while sibling result env state uses `phase_driver_write_result_env`, creating inconsistent state persistence in the same driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

