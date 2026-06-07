### FINDING_1: [OUT_OF_SCOPE] Missing tmpdir validation in retally merge writer
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `persist-retally-step3-env.sh` accepts any existing `--design-tmpdir` and performs merge writes without the newer `larch_design_tmpdir_validate` hardening used by `plan-review-continuation.sh`; exploitability is low in normal orchestration but defense-in-depth is weaker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add `larch_design_tmpdir_validate` (and canonicalize with `pwd -P`) before merge writes, matching `plan-review-continuation.sh`.

### FINDING_2: [OUT_OF_SCOPE] Auto-continuation has residual trust-boundary risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 3.5 auto-continuation re-enters review and Gate B auto-apply without an operator checkpoint between rounds; source judged this unchanged in kind from the existing auto-apply trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Prior review-round artifacts are deleted on continuation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-orchestrator-output.txt
- **Severity**: important
- **Concern**: Automatic continuation re-enters Step 3 through `run-step3-review.sh`, which deletes existing `plan-review/round-*` directories before launching the next panel. Multi-round runs therefore lose prior-round classification, timing, summary, and voting artifacts even though round counters advance and future pruning/diagnostics need stable per-round history.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Preserve completed round dirs on continuation or scope cleanup to the next round only; pass round-num from review-round-count.txt.
  - From dyn-orchestrator-output.txt: Stop wholesale `round-*` deletion on auto-continuation re-entry (delete only the active round slot, or archive completed rounds), and extend harness coverage to assert round-1 artifacts remain after an automatic round-2 entry.

### FINDING_4: `--approve` suppresses continuation after accepted Important findings
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `plan-review-continuation.sh` treats `--approve` as a hard stop before inspecting accepted findings, so an approved Gate B apply with substantial accepted findings can proceed toward Gate C without re-reviewing the revised plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Do not treat approve_requested=true as a hard stop; defer explicit review or run the same continuation heuristic after explicit Gate B settled paths.

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

### FINDING_7: Invalid design classification defaults to HARD continuation tier
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `design_classification` is missing or corrupt, continuation defaults to HARD, which can silently force extra automatic review rounds for otherwise SIMPLE runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Default classification fail-safe to SIMPLE or stop continuation with a warning on parse failure

### FINDING_8: Concern-text fallback can false-positive high accepted counts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Unstructured finding text containing terms like “high-level” can be counted as high/important by fallback parsing, triggering unnecessary continuation despite latent or nit intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Require structured Severity before high-accepted, or tighten fallback patterns

### FINDING_9: Auto-continuation bypasses Step 3 pause/timing prelude
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Automatic Step 3 continuation launches another review without the normal Step 3 entry fence that handles pause requests and timing state, so a `.pause-requested` created after Gate B can be ignored until after another long review panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Route automatic continuation through the Step 3 prelude or add the same env-source, pause-save, and timing operations before run-step3-review.sh --no-preview.

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

### FINDING_12: Final-summary fallback for missing Focus area is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Production finding blocks can omit `- **Focus area**:`, but the final-summary block-count fallback lacks a regression fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a fixture with Concern-only FINDING block and assert non-zero Plan review line.

### FINDING_13: Important-accepted continuation threshold diverges from `/implement`
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: important
- **Concern**: `plan-review-continuation.sh` continues on any single Important/High accepted finding, while `/implement` treats high findings as substantial only at `high_n >= 2`; this contradicts the stated symmetry goal and can add unnecessary panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: Align the continue threshold with `/implement` (`HIGH_ACCEPTED_COUNT >= 2`, or share a single constants/helper), and add a harness case for “1 Important → stop” vs “2 Important → continue”.

### FINDING_14: Round cursor and review-round counter can desynchronize
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: important
- **Concern**: Gate C prose expects `plan-after-round-<cursor>.txt` snapshots to advance HARD runs, but production Gate B paths do not call `snapshot-plan-round.sh write-after`; automatic loops can keep passing round 1 to `plan-review-loop.sh` while `review-round-count.txt` advances separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: After each Gate B post-apply fence, call `snapshot-plan-round.sh write-after --round "$STEP3_REVIEW_ROUND_NUM"` (and advance `write-cursor`), or drop the dead cursor branch and key `plan-review-loop` off `review-round-count.txt` only.

### FINDING_15: Structural/large-change continuation uses static metadata instead of post-apply delta
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: latent
- **Concern**: Continuation infers structural change from plan size, diff size, or HARD classification rather than measuring the actual post-Gate-B delta, so it can continue after small/no changes or miss large rewrites that fall outside static thresholds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: Either snapshot pre/post Gate B plan bodies and compare line deltas for continuation, or document and test that `/design` intentionally uses a cheaper static proxy and accept the behavioral drift.

### FINDING_16: No churn guard for oscillating review rounds
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: latent
- **Concern**: The design continuation loop lacks an `/implement`-style guard that warns or stops when accepted findings increase between rounds, so oscillating panels can consume the cap without an operator-visible convergence signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: Persist per-round `ACCEPTED_COUNT` in `plan-review/round-N/round-summary.env` (once round retention is fixed) and add a continuation veto or warning when accepted count increases without convergence, matching `review-and-fix.sh` Part C semantics.

### FINDING_17: [OUT_OF_SCOPE] `write-after` caller appears absent outside tests
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: latent
- **Concern**: `snapshot-plan-round.sh write-after` is documented as part of the Gate B / `design-postplan-emit.sh` surface, but no shipped shell caller appears to invoke it outside tests; source marked this as predating the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Test stub uses invalid loop status
- **Reviewer(s)**: dyn-orchestrator-output.txt
- **Severity**: nit
- **Concern**: `test-step3-review-cap.sh` stubs `LOOP_STATUS=converged`, which is not a valid `plan-review-loop.sh` terminal status, making the test fixture misleading though not production-path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-output.txt: Address the concern above.

### FINDING_19: Successful MainAgent retally leaves accepted-count env keys stale
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: latent
- **Concern**: After successful MainAgent re-tally, env files update status fields but do not recompute `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `NIT_ACCEPTED_COUNT`, or `NON_NIT_ACCEPTED_COUNT`; disk artifacts can be non-empty while env consumers still see zero or stale counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: After successful merge, recompute accepted / important / nit / non-nit counts from `accepted-plan-findings.md` (reuse the awk helpers from `plan-review-loop.sh`) and write them into both env files in `_rewrite_env_file`, mirroring the tally-error zeroing path.

### FINDING_20: Cumulative in-scope findings are not deduplicated across rounds
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: latent
- **Concern**: `_accumulate_round_accepted_all` concatenates accepted in-scope findings across rounds without block-level deduplication, while OOS paths deduplicate; repeated/reworded findings can inflate final-summary Plan review counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Add block-level dedup for in-scope findings in `_accumulate_round_accepted_all` and/or `_merge_retally_accepted_all` (e.g., normalized Concern text, matching the OOS Description-key approach), or renumber/dedup when writing cumulative artifacts so `render-final-summary.sh` counts unique findings.

### FINDING_21: [OUT_OF_SCOPE] Cumulative artifact retains Gate B skipped findings until render
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: nit
- **Concern**: `accepted-plan-findings-all.md` is appended before Gate B and retains skipped findings until `render-final-summary.sh` filters them, a pre-existing contract choice made more visible by multi-round accumulation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Continuation heuristic asymmetry predates artifact work
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: important
- **Concern**: The design continuation helper’s one-Important and degraded-panel continuation thresholds diverge from the cited `/implement` thresholds; source marked this as outside its artifact/env consistency scope and not a regression in that area.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.
