### FINDING_1: Step 3 harness still expects a third round
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Round Cap Invariant, Codex-dyn-Round Cap Invariant
- **Severity**: blocking
- **Concern**: `make test-step3-review-cap` still encodes escalated HARD reviews as a round-3 path, so the cap-2 change will break the CI harness unless those expectations move to round 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/scripts/test-step3-review-cap.sh`: invert/remove the round-3-reachable case, keep cap-reached-at-2 coverage, update escalation continuation expectations to cap 2
  - From Codex-Arch: Add these files to firm updates; change expectations to cap 2 and no round 3 launch; run the affected harnesses or pytest selection
  - From Cursor-Innovation: Add `### UPDATED: skills/design/scripts/test-step3-review-cap.sh`: invert or remove round-3-reachable cases; expect cap 2 on escalation; keep cap-at-2 blocking tests. Add make test-step3-review-cap to Testing strategy.
  - From Codex-Innovation: Add these files to UPDATED. Change HARD and escalation expectations to cap 2, including no round-3 dispatch for recorded escalation. Preserve accepted-finding count fixtures that are not cap assertions.
  - From Cursor-Pragmatic: Add `### UPDATED: skills/design/scripts/test-step3-review-cap.sh`: drop round-3-reachable expectations; assert cap-reached at round 2 and REVIEW_ROUND_CAP=2 on escalation paths
  - From Codex-Pragmatic: Add this file to the plan, rewrite the escalated-HARD case to assert cap-reached at round 2 with no round-3 launch, and add make test-step3-review-cap to targeted validation
  - From Cursor-Requirements: Add `### UPDATED: skills/design/scripts/test-step3-review-cap.sh`: invert HARD escalation cases to assert round 3 never launches, `REVIEW_ROUND_CAP=2`, and persisted `round_cap` stays 2; drop continuation checks for `REVIEW_ROUND_CAP=3` and `round_cap != 3`
  - From Codex-Requirements: Add this harness to the firm updates, flip the escalation assertions to cap 2 with no round-3 launch, expect `REVIEW_ROUND_CAP=2` and `round_cap 2`, and include make test-step3-review-cap in targeted validation
  - From Cursor-dyn-Round Cap Invariant: Add `### UPDATED: skills/design/scripts/test-step3-review-cap.sh`: invert/remove the HARD round-3-reachable case, expect cap-reached at round-2 boundary with escalation, and assert `REVIEW_ROUND_CAP=2`; include make test-step3-review-cap in the testing strategy
  - From Codex-dyn-Round Cap Invariant: Add this harness to firm updates and invert the escalation case so recorded HARD escalation still stops at round 2 and persists and emits cap 2


### FINDING_2: Review pipeline HARD tests still pin cap 3
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The `python/tests/review/test_review_pipeline.py` shard still asserts HARD-specific cap-3 behavior, so the review-pipeline Makefile targets will fail after the cap change unless those assertions move to 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/tests/review/test_review_pipeline.py` (or extend Testing strategy): expect `PANEL_ROUND_CAP=2`, `EFFECTIVE_ROUND_CAP=2`, and cap-reached for HARD at round 2
  - From Codex-Arch: Add these files to firm updates; change expectations to cap 2 and no round 3 launch; run the affected harnesses or pytest selection
  - From Cursor-Innovation: Explicitly update escalation continuation assertions to `REVIEW_ROUND_CAP=2` and adjust comments that cite HARD's 3 rounds (e.g. line 2920).
  - From Codex-Innovation: Add these files to UPDATED. Change HARD and escalation expectations to cap 2, including no round-3 dispatch for recorded escalation. Preserve accepted-finding count fixtures that are not cap assertions.
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/review/test_review_pipeline.py` and run those harness targets in the test plan
  - From Cursor-Requirements: Add `### UPDATED: python/tests/review/test_review_pipeline.py` and run `python3 -m pytest python/tests/review/test_review_pipeline.py -k 'dispatch_panel_hard or tier_cap_controls'`
  - From Codex-Requirements: Add `### UPDATED: python/tests/review/test_review_pipeline.py` and run `python3 -m pytest python/tests/review/test_review_pipeline.py -k 'dispatch_panel_hard or tier_cap_controls'`


### FINDING_4: Implement token-propagation harness still expects cap 3
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The implement token-propagation harness still expects HARD cap 3, so `make test-implement-review-token-propagation` stays red after HARD is capped at 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.sh` with expected cap 2 for HARD
  - From Codex-Arch: Add these files to firm updates; change expectations to cap 2 and no round 3 launch; run the affected harnesses or pytest selection
  - From Codex-Innovation: Add these files to UPDATED. Change HARD and escalation expectations to cap 2, including no round-3 dispatch for recorded escalation. Preserve accepted-finding count fixtures that are not cap assertions.


### FINDING_5: Design gate docs still authorize round 3
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Round Cap Invariant, Codex-dyn-Round Cap Invariant
- **Severity**: important
- **Concern**: The approval-gates and flags design docs still authorize round 3 or say HARD=3, leaving operator guidance stale after the cap becomes universal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/design/references/approval-gates.md` (and `skills/design/references/flags.md:90`): replace HARD=3 / round-3 authorization with fixed cap 2; include `skills/implement/scripts/step-5-review.sh:59` banner and `skills/review/references/heavy-worker.md` tier-cap prose in the grep-driven doc sweep
  - From Codex-Arch: Add firm updates for both references and rewrite to fixed cap 2; remove round 3 authorization language while keeping HARD panel and model-role differences
  - From Cursor-Innovation: Add `### UPDATED: skills/design/references/approval-gates.md` replacing round-3 authorization with cap-2-only wording (escalation still affects tier/model role, not round count).
  - From Codex-Innovation: Add `### UPDATED: skills/design/references/approval-gates.md` replacing round-3 authorization with cap-2-only wording (escalation still affects tier/model role, not round count).
  - From Cursor-Requirements: Add `### UPDATED: skills/design/references/approval-gates.md` under Review-round cap: all tiers cap at 2; escalation changes panel tier/role only, never a third round
  - From Codex-Requirements: Add `### UPDATED: skills/design/references/approval-gates.md` under Review-round cap: all tiers cap at 2; escalation changes panel tier/role only, never a third round
  - From Cursor-dyn-Round Cap Invariant: Add `### UPDATED: skills/design/references/approval-gates.md` and state re-run eligibility uses the fixed cap of 2 with no round-3 carve-out
  - From Codex-dyn-Round Cap Invariant: Add `### UPDATED: skills/design/references/approval-gates.md` and state re-run eligibility uses the fixed cap of 2 with no round-3 carve-out


### FINDING_6: Step 5 runtime banner and contract still print 2/2/3
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Round Cap Invariant, Codex-dyn-Round Cap Invariant
- **Severity**: important
- **Concern**: The `/implement` Step 5 wrapper still prints and documents a tier cap of `2/2/3`, so every normal run keeps advertising a third HARD round even after the policy changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Also update `skills/implement/scripts/step-5-review.sh` and sibling `skills/implement/scripts/step-5-review.md` to a fixed cap of 2 for every tier.
  - From Codex-Arch: Add these runtime surfaces to UPDATED and replace the stale text with fixed cap 2 for every tier. Update the step-5-review.md contract in sync with the banner.
  - From Cursor-Innovation: Also update `skills/implement/scripts/step-5-review.sh` and sibling `skills/implement/scripts/step-5-review.md` to a fixed cap of 2 for every tier.
  - From Codex-Innovation: Also update `skills/implement/scripts/step-5-review.sh` and sibling `skills/implement/scripts/step-5-review.md` to a fixed cap of 2 for every tier.
  - From Cursor-Pragmatic: Update `step-5-review.sh` and `skills/implement/scripts/step-5-review.md` to print a fixed cap of 2 (plan lists implement/SKILL.md but not these runtime wrappers)
  - From Codex-Pragmatic: Add both wrapper files to firm updates and replace the banner and contract wording with fixed cap 2, then keep the final cap grep clean
  - From Cursor-Requirements: Add `### UPDATED: skills/implement/scripts/step-5-review.sh` and sibling `skills/implement/scripts/step-5-review.md` to replace `2/2/3` with a fixed cap of 2
  - From Codex-Requirements: Add both wrapper files to firm updates and replace the banner and contract wording with fixed cap 2, then keep the final cap grep clean
  - From Cursor-dyn-Round Cap Invariant: Update `step-5-review.sh` and `skills/implement/scripts/step-5-review.md` to print a fixed cap of 2 (plan lists implement/SKILL.md but not these runtime wrappers)
  - From Codex-dyn-Round Cap Invariant: Add both wrapper files to firm updates and change the banner and contract to fixed cap 2 wording.


### FINDING_7: Plan-review continuation tests still pin REVIEW_ROUND_CAP=3
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan-review escalation continuation tests still assert `REVIEW_ROUND_CAP=3`, so that targeted pytest shard will fail once HARD is capped at 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Explicitly update escalation continuation assertions to `REVIEW_ROUND_CAP=2` and adjust comments that cite HARD's 3 rounds (e.g. line 2920).


### FINDING_9: /review heavy-worker contract still documents 2/2/3
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Round Cap Invariant, Codex-dyn-Round Cap Invariant
- **Severity**: important
- **Concern**: The `/review --subagent` heavy-worker reference still advertises a `2/2/3` tier cap, so the subagent path can keep steering HARD reviews toward a third round even if the parent skill prose changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add UPDATED: `skills/review/references/heavy-worker.md` and replace the cap text with fixed cap 2, preserving the existing HARD panel/model-role differences
  - From Cursor-Pragmatic: Add UPDATED: `skills/review/references/heavy-worker.md` and replace the cap text with fixed cap 2, preserving the existing HARD panel/model-role differences
  - From Codex-Pragmatic: Add UPDATED: `skills/review/references/heavy-worker.md` and replace the cap text with fixed cap 2, preserving the existing HARD panel/model-role differences
  - From Cursor-Requirements: Add this file to firm updates and change the worker wording to reuse the parent ROUND_CAP or state fixed cap 2 for every tier
  - From Codex-Requirements: Add this file to firm updates and change the worker wording to reuse the parent ROUND_CAP or state fixed cap 2 for every tier
  - From Cursor-dyn-Round Cap Invariant: Add `### UPDATED: skills/review/references/heavy-worker.md` replacing 2/2/3 with fixed cap 2 prose
  - From Codex-dyn-Round Cap Invariant: Add this reference to firm updates and state that ROUND_CAP is fixed at 2 for every tier while keeping HARD's model and panel shape only.

### FINDING_1: Update continuation tests for the universal cap-2 branch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The continuation/escalation tests still assume a third review round after HARD is flattened to a cap of 2. At `review_count == 2`, the escalation branch no longer runs, so these cases should either expect `cap-reached` or seed `review_count=1` for the continue-true path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite `test_continuation_escalates_on_cumulative_hi<REDACTED-TOKEN>` and `test_continuation_continues_when_a_new_finding_appears` round-2 expectations to `PLAN_REVIEW_CONTINUE=false`, `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, and `REVIEW_ROUND_CAP=2`; keep round-1 continue assertions unchanged.
  - From Cursor-Arch: Change the escalation continuation case to expect `PLAN_REVIEW_CONTINUE=false`, `PLAN_REVIEW_CONTINUE_REASON=cap-reached`, `REVIEW_ROUND_CAP=2`, and `append_escalation` writing `round_cap: 2`; update `test-step3-review-cap.md` to match.
  - From Cursor-Pragmatic: Rewrite this case explicitly: seed review_count=1, expect escalation to HARD with REVIEW_ROUND_CAP=2 and persisted round_cap=2, or expect cap-reached when count already equals 2. Name this subsection in the plan’s test-step3-review-cap.sh update bullet.
  - From Cursor-Requirements: Restructure those escalation cases: seed review_count=1 when the test still needs continue=true after escalation to HARD, assert REVIEW_ROUND_CAP=2, and keep a separate review_count=2 case that expects PLAN_REVIEW_CONTINUE=false with cap-reached; document that split in both test file rows


### FINDING_3: Refresh stale plan-review prose for the cap-2 world
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The tiered plan-review documentation still describes HARD as cap 3 and references round-3 pruning. That prose is stale once all tiers are capped at 2 and will mislead operators and readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When rewriting `plan-review.md`, change HARD to cap 2 and delete or reword the `round-3 pruning` sentence so pruning is described only for round 2 under a universal cap of 2.


