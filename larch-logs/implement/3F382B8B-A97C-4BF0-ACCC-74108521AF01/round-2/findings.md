### FINDING_1: Security-tagged accepted findings leak through public summary bucket
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The public `/design` final summary now includes security focus-area accepted findings in bucketed Plan review counts, potentially signaling accepted security-classified review items on a tracking issue even when finding text remains local.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: Structural/large-change continuation predicate is too broad
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `plan-review-continuation.sh` can schedule another full review panel for any accepted finding when size/tier signals fire, so small or nit-only rounds on large plans may fail to converge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: Single-important accepted finding triggers continuation despite `/implement` threshold ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-artifact-accounting-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: important
- **Concern**: The design continuation helper treats `HIGH_ACCEPTED_COUNT > 0` as substantial, while `/implement` uses `high_n >= 2` unless other structural/fix-count signals apply. This can force extra design review rounds for a single important finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-artifact-accounting-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_4: Partial missing Severity metadata globally demotes parsing to fragile concern-text fallback ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: If any finding block lacks a structured Severity line, the helper falls back for the whole round and may match benign concern text such as “high-level,” inflating important/high accepted counts and triggering unnecessary continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt: Address the concern above.

### FINDING_5: Degraded zero-accepted rounds can continue until cap ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: A degraded panel currently continues automatically until the shared cap even when no findings were accepted and no Gate B apply occurred, potentially burning all review slots without improving the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt: Address the concern above.

### FINDING_6: Continuation predicate harness lacks small-clean/core predicate coverage ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Test coverage does not adequately pin the small-clean stop path or core continuation reasons such as non-nit count, structural/large-change, and related resume marker edges, so predicate drift could silently cause over-review or premature convergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-state-machine-output.txt: Address the concern above.

### FINDING_7: Gate B zero-findings/degraded-panel prose bypasses continuation helper
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` and `SKILL.md` still describe zero-findings or degraded-panel Gate B exits as proceeding directly to Step 3b/Gate C, conflicting with the new continuation-helper contract and allowing automatic re-review to be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_8: `--approve` suppresses automatic continuation after explicit apply
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: In explicit approve mode, accepted important findings can be applied and then flow to Gate C without running the automatic continuation heuristic, preserving old prompt-driven behavior instead of the new loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: MainAgent re-tally accepted findings are not reflected in cumulative accepted-all file
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After MainAgent re-tally, `accepted-plan-findings-all.md` may not be updated even though final summary prefers it, so later-round accepted findings can be omitted from the final Plan review count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Final summary ignores cumulative accepted findings when `voting-tally.md` is absent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-artifact-accounting-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` still gates Plan review counting on `voting-tally.md`, but cap-reached cleanup can delete that tally while leaving `accepted-plan-findings-all.md`, causing a final summary of `0 findings` despite cumulative accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-artifact-accounting-output.txt: Address the concern above.

### FINDING_11: Automatic continuation re-entry leaves stale Gate B postapply markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: latent
- **Concern**: Automatic continuation loops back without the same Step 3 entry hygiene as manual re-entry, so `.gate-b-postapply-ready-*` markers and related sentinels can survive and affect later pause/resume or idempotency behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Plan review reference still says “Single-pass review”
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/plan-review.md` retains a “Single-pass review” heading even though the design review flow now has a multi-round controller, which can mislead operators or agents reading that reference first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_13: Cumulative accepted-all can overreport findings skipped in explicit one-by-one Gate B
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If a `/design --approve` user chooses one-by-one review and skips a finding, `accepted-plan-findings.md` may be corrected while `accepted-plan-findings-all.md` still contains the skipped finding, causing final summary overreporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Multi-round integration harness remains single-pass ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: important
- **Concern**: The named multi-round integration test still only verifies a single review pass and does not exercise Gate B → continuation → second review behavior, cumulative artifacts, counters, or terminal statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_15: Structural harness does not pin new Step 3.5 continuation contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-workflow-contracts-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` lacks contains/grep pins for `plan-review-continuation.sh`, the Continue/Stop branch prose, and branch-matrix requirements, so prompt-side loop orchestration can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_16: Cumulative accepted-all restore/append behavior lacks behavioral tests ([OUT_OF_SCOPE] source included)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-artifact-accounting-output.txt
- **Severity**: important
- **Concern**: The new `accepted-plan-findings-all.md` accumulation, restore, append, and manual-reset semantics are not covered by behavioral tests, leaving stale or missing cumulative findings possible after failures or sequential rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-artifact-accounting-output.txt: Address the concern above.

### FINDING_17: Direct review entry cleanup of accepted-all lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `design-step3-state.sh --direct-review-entry` now deletes `accepted-plan-findings-all.md`, but the corresponding harness does not seed and assert that cleanup, so stale cumulative findings could later leak into final summary if cleanup regresses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: Gate B postapply pause/resume path skips continuation check
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: The resume branch for `.gate-b-postapply-ready-*` can jump from the post-apply fence to Step 3b without invoking `plan-review-continuation.sh`, skipping automatic rounds after a pause/resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_19: Manual re-entry does not reset cumulative review artifacts consistently
- **Reviewer(s)**: dyn-state-machine-output.txt, dyn-artifact-accounting-output.txt
- **Severity**: important
- **Concern**: Manual Gate C/Gate A re-review can append to or preserve prior cumulative artifacts such as `accepted-plan-findings-all.md` and OOS cumulative files, causing final summary to include findings from superseded review runs instead of overwriting them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt, dyn-artifact-accounting-output.txt: Address the concern above.

### FINDING_20: Panel-failed rounds consume review cap without review/apply benefit
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `LOOP_STATUS=panel-failed` persists the incremented review round counter while bypassing Gate B and continuation, so repeated panel failures can exhaust the shared cap and leave stale artifacts with no successful review round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Design loop lacks churn warning analogous to `/implement`
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: nit
- **Concern**: `/design` automatic continuation has no operator-visible churn signal when later rounds accept more findings than earlier rounds, unlike `/implement` Step 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_22: Cumulative in-scope accepted findings are not deduplicated across rounds
- **Reviewer(s)**: dyn-artifact-accounting-output.txt
- **Severity**: latent
- **Concern**: `accepted-plan-findings-all.md` appends in-scope accepted findings without deduplication, so materially similar findings re-accepted in later rounds can inflate final Plan review totals unless the file is explicitly documented as a per-round audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-accounting-output.txt: Address the concern above.

### FINDING_23: Round forensics allowlist omits cumulative accepted-all artifact
- **Reviewer(s)**: dyn-workflow-contracts-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-design-round-artifacts.md` includes `accepted-plan-findings.md` but not the new cumulative `accepted-plan-findings-all.md`, so multi-round accepted findings may be absent from committed per-round forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Linting docs still describe old tiered cap behavior
- **Reviewer(s)**: dyn-workflow-contracts-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still says the Step 3 review cap test covers HARD-tier blocking on the sixth entry even though the cap is now flattened to 5 for both tiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contracts-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Approval-gates binding convention still references per-tier cap behavior
- **Reviewer(s)**: dyn-workflow-contracts-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md` still references “per-tier behavior” for review-round caps even though cap prose was flattened elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contracts-output.txt: Address the concern above.
