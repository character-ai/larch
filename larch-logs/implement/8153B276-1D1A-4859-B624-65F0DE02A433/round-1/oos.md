### FINDING_1: Step 5c rejoin hides fresh retries
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-bgjob-design
- **Severity**: major
- **Concern**: Existing `design-step5c.result.env` causes the launcher to rejoin `bgjob wait` on any rerun, so Fix-and-retry/Override or publish-failure retries replay stale `DONE` output instead of starting a fresh Step 5c unless the result env is cleared or rejoin is gated by a live identity-valid registry row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-design: Treat “result env exists” as rejoin-only when a live identity-valid registry row exists (or add an explicit `--fresh-start` / pre-start `rm` contract wired into validator Fix-and-retry/Override). Mirror the Step 3 stale-merge harness (`test-design-step3-review.sh` `D_STALE`) so a fresh child cannot be satisfied by a prior `design-step5c.result.env`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_2: Step 4 tail rejoin needs required Gate C keys
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-design
- **Severity**: major
- **Concern**: Existing `design-step4-tail.result.env` can short-circuit recovery even when the required Gate C keys are missing, so pause/retry can replay stale `DONE` output instead of regenerating `SKIP_APPROVE_REQUESTED_GATEC` and related KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-bgjob-design: Rejoin on existing result env only when the registry row is still live; otherwise require required KVs (`SKIP_APPROVE_REQUESTED_GATEC`, `GATEC_PREVIEW_PATH`, rejected-findings markers) before skipping a fresh tail launch, and clear `bgjob/design-step4-tail.result.env` on intentional recovery re-emits.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Pause-save stamps success before merge KVs
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `design-step3b-tail` can exit 0 from pause-save before the merge env is written, while the bgjob still stamps `BGJOB_RC=0` and the Step 4 sentinel, so resume or Gate C can observe success without `SKIP_APPROVE_REQUESTED_GATEC` or preview KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Step 6 cleanup trusts sidecar status
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-design
- **Severity**: major
- **Concern**: Step 6 still decides in-flight / cleanup state from the step5c sidecar or a bare result-env presence, rather than requiring the bgjob result env and `BGJOB_RC=0`, so stale sidecar KVs can authorize cleanup while the child is not truly complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bgjob-design: Read status through the same preference chain as `read_result_env_main` (`design_terminal.py:764-775`), require a regular `bgjob/design-step5c.result.env` with `BGJOB_RC=0` before honoring `PLAN_WRITE_OK` / `CLEANUP_ELIGIBLE`, and keep `_step6_in_flight` true until both terminal sentinel and result env agree.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Step 5c harness codifies rejoin
- **Reviewer(s)**: dyn-dyn-bgjob-design
- **Severity**: minor
- **Concern**: The harness asserts that an existing `design-step5c.result.env` must route to `bgjob wait DONE` instead of relaunch, so stale-retry cases are not covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-design: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Step 6 in-flight precedence is weakened
- **Reviewer(s)**: dyn-dyn-bgjob-design
- **Severity**: minor
- **Concern**: `_step6_in_flight` returns `False` when a `design-step5c.result.env` exists even if `.completed/step-5c-terminal` is absent and a live registry row remains, so the old terminal-sentinel precedence is weakened if a caller can observe result env before the daemon finishes writing the sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-design: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

