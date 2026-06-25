# Review Round 3

- Mode: `diff`
- 6 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Postplan promotion does not reconcile drafter_pick against final plan.txt
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-dialectic-lifecycle
- **Severity**: important
- **Concern**: `promote_candidates()` / `write_candidates()` re-stamp `plan_fingerprint` from final `plan.txt` bytes but do not revalidate `drafter_pick`, option labels, or tradeoff text against the post-postplan plan. After validator auto-fix or inline retry rewrites the plan body, a preserved `.dialectic-raw-pending.json` can be promoted with a fresh fingerprint but stale fork semantics (for example the final plan already follows option B while `drafter_pick` still names option A). Gate C may then debate the wrong fork and misstate CHOSEN/THESIS mapping in the digest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-validate each decision against final plan.txt at promote time; drop raw sidecar and emit fail reason when pick no longer aligns.
  - From dyn-dyn-dialectic-lifecycle: After postplan, before promotion, re-validate each decision against final `plan.txt` (reuse `_infer_manual_drafter_pick()`-style checks or drop candidates when pick/options no longer match the plan). Fail open by skipping promotion when reconciliation fails.


### FINDING_3: step2b_drafter_main ignores dialectic promotion failure after POSTPLAN_RC=0
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `step2b_drafter_main` ignores `dialectic-promote-candidates` failure after `POSTPLAN_RC=0`. Promotion can emit `DIALECTIC_CANDIDATES_WRITTEN=false` while Step 2b still reports succeeded, so Gate C never debates a drafter-declared fork.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Parse promote KV output; warn or fail when dialectic was parsed but promotion did not write candidates.


### FINDING_4: Missing lifecycle integration tests for dialectic cleanup, promotion gating, and fingerprint binding
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-generic, dyn-dyn-dialectic-lifecycle
- **Severity**: important
- **Concern**: Plan-required `python/test_design_lifecycle.py` integration coverage for dialectic artifact cleanup at drafter start, `step2b_drafter_main` promoting only after `POSTPLAN_RC=0`, and post-postplan `plan_fingerprint` binding is still missing beyond prompt-text snapshot coverage. Regressions in `design_lifecycle.py` cleanup list, promotion gate, or promotion ordering after `_shared_step2b_postplan_body` could pass CI while only unit tests in `test_design_dialectic.py` pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add lifecycle tests for artifact cleanup, promote-after-postplan-only, and post-postplan fingerprint binding.
  - From cursor-specialist-edge-cases: Add lifecycle tests for cleanup promotion gate and postplan rewrite fingerprint per acceptance criteria.
  - From cursor-specialist-testing: Add monkeypatched step2b_drafter_main tests for artifact cleanup promotion-only-on-POSTPLAN_RC=0 and final plan_fingerprint binding.
  - From codex-generic: Add `python/test_design_lifecycle.py` coverage that exercises drafter-start cleanup and post-postplan promotion from `.dialectic-raw-pending.json`, including a postplan rewrite case that asserts the promoted fingerprint matches final `plan.txt` bytes.
  - From dyn-dyn-dialectic-lifecycle: Add focused `test_design_lifecycle.py` cases that mock postplan success/failure, assert cleanup unlinks dialectic artifacts at drafter start, assert promotion runs only on `POSTPLAN_RC=0`, and assert promoted `plan_fingerprint` matches post-postplan `plan.txt` after a simulated rewrite plus `clear_stale()`.


### FINDING_5: Resume Gate C guidance conflicts on Step 4 tail vs digest-from-disk
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: Resume Gate C guidance in `skills/design/references/approval-gates.md` conflicts with `SKILL.md` on whether to re-run the Step 4 tail vs read digest from disk only. `resume@4b` can re-invoke tail and duplicate cached digest/preview in orchestrator context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Unify resume contract: preview recovery without duplicate digest emit, or digest file read plus standalone preview.


### FINDING_7: Manual debate drafter_pick inference uses naive substring matching
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Free-form manual debate infers `drafter_pick` via naive substring search in `plan.txt` (Option label file matches profile in plan text). Manual debate can map CHOSEN to the wrong side and skew advisory digest and ballot semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Use word-boundary or tokenized matching or fail closed when inference is ambiguous; add regression test.


### FINDING_8: Duplicate-vote conflict handling still allows malformed judge votes to count
- **Reviewer(s)**: codex-generic
- **Severity**: important
- **Concern**: The duplicate-vote fix in `python/design_dialectic.py:657-662` is incomplete. A judge output like `DECISION_1: THESIS`, then `DECISION_1: ANTI_THESIS`, then `DECISION_1: THESIS` deletes the first vote on conflict, then re-adds the later vote, so one malformed judge can still count toward the 2-of-3 threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic: Track conflicted `(judge, decision_id)` keys in a separate invalid set, and ignore all later lines for that key once conflicting tokens appear.


