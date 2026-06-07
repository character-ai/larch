# Review Round 5

- Mode: `diff`
- 7 accepted, 9 rejected (3 neutral)

## Accepted Findings

### FINDING_10: Multi-round orchestration lacks end-to-end regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Existing/added tests do not prove the real continuation path re-enters Step 3, launches a second review, defers Gate C, preserves cap semantics, and avoids stale single-pass assumptions; CI could pass while the new multi-round behavior is skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend the integration harness with a stubbed continuation→second-review path and update the sibling .md contract away from single-pass-only wording.
  - From cursor-specialist-testing-output.txt: Add a stubbed cross-script case chaining continuation helper, design-step3-state --auto-continuation-entry, and a second driver invocation.
  - From codex-specialist-testing-output.txt: Add a structural or integration regression that proves the continue branch runs auto-continuation-entry, invokes a second run-step3-review.sh --no-preview, defers Gate C, and consumes the shared counter once per launched round.


### FINDING_11: Structured Severity important continuation path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Continuation tests only cover concern-text fallback for high accepted findings, not structured `- **Severity**: important`, so the intended structured severity path could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a continuation fixture with - **Severity**: important and expect PLAN_REVIEW_CONTINUE=true / reason=high-accepted below cap.


### FINDING_14: Round cursor and review-round counter can desynchronize
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: important
- **Concern**: Gate C prose expects `plan-after-round-<cursor>.txt` snapshots to advance HARD runs, but production Gate B paths do not call `snapshot-plan-round.sh write-after`; automatic loops can keep passing round 1 to `plan-review-loop.sh` while `review-round-count.txt` advances separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: After each Gate B post-apply fence, call `snapshot-plan-round.sh write-after --round "$STEP3_REVIEW_ROUND_NUM"` (and advance `write-cursor`), or drop the dead cursor branch and key `plan-review-loop` off `review-round-count.txt` only.


### FINDING_3: Prior review-round artifacts are deleted on continuation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-orchestrator-output.txt
- **Severity**: important
- **Concern**: Automatic continuation re-enters Step 3 through `run-step3-review.sh`, which deletes existing `plan-review/round-*` directories before launching the next panel. Multi-round runs therefore lose prior-round classification, timing, summary, and voting artifacts even though round counters advance and future pruning/diagnostics need stable per-round history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Preserve completed round dirs on continuation or scope cleanup to the next round only; pass round-num from review-round-count.txt.
  - From dyn-orchestrator-output.txt: Stop wholesale `round-*` deletion on auto-continuation re-entry (delete only the active round slot, or archive completed rounds), and extend harness coverage to assert round-1 artifacts remain after an automatic round-2 entry.


### FINDING_5: HARD structural continuation fires for nit-only accepted sets
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On HARD designs, first-round structural continuation can trigger for any accepted findings, including nit-only sets, causing extra rounds where `/implement` would converge on zero Important and few non-nit findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Narrow structural continuation to non-nit or high-severity accepted findings, or align thresholds with implement convergence constants


### FINDING_6: Degraded-panel continuation can burn the cap with zero accepted findings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-artifact-state-output.txt
- **Severity**: important
- **Concern**: The degraded-panel branch can continue automatically despite zero accepted findings, including after successful MainAgent retally leaves `DEGRADED_PANEL=1` stale. This can schedule repeated full review panels, consume the shared round cap, and inflate cumulative artifacts/final-summary totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a degraded retry budget or require COLLECT_OK_COUNT>0 / ACCEPTED_COUNT>0 before degraded-panel continuation
  - From dyn-artifact-state-output.txt: Either have `persist-retally-step3-env.sh` set `DEGRADED_PANEL=0` (and refresh related KVs) on successful retally when adjudication completed, or teach `plan-review-continuation.sh` to ignore `DEGRADED_PANEL` once `TALLY_PLAN_REVIEW_STATUS=ok` and `LOOP_STATUS=complete`, using only disk-derived accepted counts for the continue/stop decision.


### FINDING_9: Auto-continuation bypasses Step 3 pause/timing prelude
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Automatic Step 3 continuation launches another review without the normal Step 3 entry fence that handles pause requests and timing state, so a `.pause-requested` created after Gate B can be ignored until after another long review panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Route automatic continuation through the Step 3 prelude or add the same env-source, pause-save, and timing operations before run-step3-review.sh --no-preview.


