# Review Round 1

- Mode: `diff`
- 6 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_10: Test harness gaps for cap-hit sentinel gate and cap-at-entry
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-sentinel-routing-output.txt
- **Severity**: important
- **Concern**: `test-implement-anti-polling-rule.sh` pins the `complete`-route terminal gate on `.completed/step-3` but not the `cap-hit` gate. `test_cap_reached_short_circuit` never asserts `.completed/step-3` exists after entry-cap short-circuit. That gap let the cap-at-entry deadlock ship alongside the new routing contract; an edit could remove the cap-hit premature-notification gate while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a `check()` mirroring the complete assertion for the cap-hit branch text requiring `.completed/step-3` before Step 3b routing.
  - From dyn-sentinel-routing-output.txt: Assert `.completed/step-3` in `test_cap_reached_short_circuit`, add an anti-polling harness check for the `cap-hit` sentinel requirement, and add a negative case where `cap-hit` is returned without the sentinel.


### FINDING_2: Cap-at-entry returns `cap-hit` without writing `.completed/step-3` (deadlock)
- **Reviewer(s)**: dyn-sentinel-routing-output.txt
- **Severity**: important
- **Concern**: The post-loop matrix requires `.completed/step-3` before routing `STEP3_REVIEW_LOOP_STATUS=cap-hit` to Step 3b, but the entry-cap short-circuit never writes that sentinel. `design-step3-review.sh` maps `LOOP_STATUS=cap-reached` to `STEP3_REVIEW_LOOP_STATUS=cap-hit`; a real cap-at-entry run can have `cap-hit` / `skipped-cap-reached` in `.step3-review-result.env` with no `.completed/step-3`. The matrix is evaluated before the `LOOP_STATUS=cap-reached` block that runs `design-step3-gate-b-bypass.sh`, so a compliant orchestrator hits the recovery waiter and blocks forever on cap re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-routing-output.txt: Write `.completed/step-3` (and `step-3.5` if needed) in the cap-at-entry driver before returning `cap-hit`, or exempt entry-cap (`TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached` / `STEP3_REVIEW_CAP_REACHED=true`) from the sentinel gate and route through `design-step3-gate-b-bypass.sh` first.


### FINDING_4: Publish provenance/refusal trusts stale `.step3-review-result.env` without `.completed/step-3`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_review_provenance()` reads only `.step3-review-result.env`, not `.completed/step-3`. It maps `LOOP_STATUS=complete` to terminal status without requiring the sentinel. Publish refuses `rounds_completed=0` only when `review_status` is non-empty; a partial env with only `ROUNDS_COMPLETED=0` can publish with no provenance and no refusal. After Fix C clears the env, missing state bypasses zero-round refusal; premature Step 5c during round-2 continuation can proceed without a `review_status` footer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Refuse publish unless `.completed/step-3` exists (or env proves terminal loop completion).
  - From codex-specialist-correctness-output.txt: Return a provenance-present flag and fail closed on zero or malformed rounds even when status is missing.
  - From cursor-specialist-edge-cases-output.txt: Refuse publish when review_status is complete or cap-hit unless `(design_tmpdir / .completed / step-3).is_file()`.


### FINDING_5: Published provenance is prepended at top; implement-preflight scans only the trailer block
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `design publish` writes `review_status` / `rounds_completed` at the top of `composed-plan.md`, while `implement-preflight.sh` scans only the final metadata block before `diff_lines`. A normal reviewed plan publishes provenance that preflight never parses; retrying publish can duplicate top headers. `/implement` therefore does not see explicitly zero-review plans that carry top-of-file provenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Insert or replace provenance idempotently in the final trailer block directly above `diff_lines`, and test that implement-preflight can read design-published metadata.
  - From codex-specialist-edge-cases-output.txt: Splice the provenance into the final trailer block before `diff_lines`, before optional size trailers when present.
  - From codex-specialist-testing-output.txt: Insert or replace the provenance lines immediately above `diff_lines` and test publish output against the preflight parser.


### FINDING_6: Emergency malformed-plan fallback is incorrectly refused for zero-review provenance
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Emergency malformed-plan fallback content is still parsed for zero-review provenance after raw issue fallback content is written. A malformed issue body ending with `rounds_completed: 0` and `diff_lines: 10` is refused even though no valid `larch:plan` block was extracted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Track whether the plan came from a valid extracted block and skip provenance refusal for emergency fallback content.


### FINDING_7: `panel-init-failed` is not allowed by `_GENERIC_BAILS`
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `panel-init-failed` is used as a terminal `BAIL_REASON` but is not in `_GENERIC_BAILS`. `design-stage-terminal-state.sh` rejects the token before writing `design-failure-terminal-state.env`, so panel-init failures skip the intended `failed-judge-panel` terminal state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add `panel-init-failed` to `_GENERIC_BAILS` or use an allowed bail token, and add a runtime test for the no-anchor panel-init path.


