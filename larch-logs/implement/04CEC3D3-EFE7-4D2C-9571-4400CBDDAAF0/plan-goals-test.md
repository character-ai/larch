## Goal
Implement issue #6244: [IMPLEMENTING] Cap /implement and /design and /review to 2 review rounds, including for difficulty:hard, so review round cap does not depend on difficulty at all.

## Implementation Plan
## Plan

## Approach

Make the review round cap independent of difficulty.

1. Change the HARD tier ceiling from `3` to `2`.
2. Ensure persisted `difficulty-rating.json` records cannot keep an old `round_cap: 3` alive for resumed or already-resolved runs.
3. Update tests that assert HARD or escalated records use a cap of 3.
4. Update skill prose and public docs that still advertise `2/2/3`, "HARD caps at 3", "3-round cap", or round 3 authorization.

## Files to modify/create

### UPDATED: python/larch/core/config.py

Set `DIFFICULTY_TIER_CEILINGS[DIFFICULTY_TIER_HARD]` to `2`.

### UPDATED: python/larch/calibration/difficulty.py

Make resolved policy authoritative over stale persisted caps.

- In `_resolution_from_data`, clamp the stored `round_cap` to `min(stored, tier_ceiling(panel_tier))` so a persisted value of `3` is silently bounded to `2` on read.
- Keep `append_escalation()` writing `tier_ceiling(to_tier)`, which becomes 2 after the config change.

### UPDATED: python/tests/calibration/test_difficulty.py

Update assertions and fixtures from `round_cap: 3` to `round_cap: 2`.

Cover both direct `tier_ceiling(HARD)` and persisted resolution merge behavior so old 3-round records do not survive.

### UPDATED: python/tests/calibration/test_difficulty_calibration.py

Update report literal assertions where realized HARD rows reference cap 3. Preserve accepted-finding count semantics if those rows are about findings, not caps.

### UPDATED: python/tests/review/test_plan_review.py

Update escalation continuation assertions and test structure:
- Adjust the comment on line 2920 ("HARD's 3 rounds" → "HARD's cap of 2").
- For tests that seed `review_count=2` and expected escalation to fire (old path: `2 < 3` = True), restructure to either seed `review_count=1` (escalation still fires since `1 < 2` = True, asserting `REVIEW_ROUND_CAP=2`) or expect `PLAN_REVIEW_CONTINUE=false` with `PLAN_REVIEW_CONTINUE_REASON=cap-reached` when review_count is already 2.
- For `test_continuation_escalates_on_cumulative_hi<REDACTED-TOKEN>` and `test_continuation_continues_when_a_new_finding_appears`: split into round-1 continuation (escalation fires, `REVIEW_ROUND_CAP=2`) and round-2 cap-reached expectations.
- Assert that `append_escalation` writes `round_cap: 2` for HARD tier escalations.
- Keep the duplicate-finding convergence intent unchanged.

### UPDATED: python/tests/review/test_review_pipeline.py

Update HARD-specific cap-3 assertions (`PANEL_ROUND_CAP`, `EFFECTIVE_ROUND_CAP`) to cap 2. Expect cap-reached for HARD at round 2.

### UPDATED: skills/design/scripts/test-step3-review-cap.sh

Invert or remove the round-3-reachable escalation case. Assert cap-reached at round 2 boundary for HARD escalation. Expect `REVIEW_ROUND_CAP=2` on escalation paths. Remove any continuation checks for `REVIEW_ROUND_CAP=3`. Where the test currently seeds `review_count=2` for an escalation continue-true path, restructure to seed `review_count=1` and assert `REVIEW_ROUND_CAP=2` and `round_cap: 2` in the persisted difficulty record.

### UPDATED: skills/design/scripts/test-step3-review-cap.md

Update the sibling contract doc to match the .sh changes: cap 2 for all tiers, no round-3-reachable case.

### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.sh

Update expected HARD cap from 3 to 2 so the harness passes after the config change.

### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.md

Update sibling contract doc to match the .sh changes.

### UPDATED: skills/design/references/approval-gates.md

Under "Review-round cap": state that all tiers cap at 2 and remove round-3 authorization language. Escalation changes panel tier and model role only, not round count.

### UPDATED: skills/design/references/flags.md

Remove or rewrite any line that states HARD has cap 3 or that escalation authorizes a third round.

### UPDATED: skills/design/references/plan-review.md

Replace cap prose with cap 2 for all tiers.

- Change `2/2/3` to `2/2/2` or plain "cap 2".
- Update the tiered panel section so HARD keeps its Codex default role and pair shape, but no longer gets cap 3.
- Remove wording that round 3 can be authorized by escalation.
- Delete or reword the "round-3 pruning" sentence (previously: "Escalated rounds skip pruning; round-3 pruning uses the prior rounds ledger"). Under the universal cap of 2, pruning applies only for round 2; there is no round 3 in any tier.

### UPDATED: skills/design/SKILL.md

Update the Step 2b difficulty prose so HARD no longer caps at 3. Keep the non-goal intact: HARD still affects reviewer model role and panel shape where current policy says so.

### UPDATED: skills/implement/scripts/step-5-review.sh

Update the banner that currently prints "tier cap 2/2/3, HARD's 3-round cap a hard ceiling" to reflect a fixed cap of 2 for every tier.

### UPDATED: skills/implement/scripts/step-5-review.md

Update the sibling contract doc to match the banner change.

### UPDATED: skills/review/SKILL.md

Update wrapper-loop prose from `2/2/3` to a fixed cap of 2 for every tier.

### UPDATED: skills/review/references/heavy-worker.md

Update tier-cap prose from `2/2/3` to fixed cap 2 for every tier. Keep HARD panel/model-role differences intact.

### UPDATED: skills/implement/SKILL.md

Update Step 5 prose from `2/2/3` and "HARD's 3-round cap" to a fixed cap of 2 for every tier.

### UPDATED: README.md

Update the `/implement` public feature row if it still advertises `2/2/3` or a HARD cap of 3.

### UPDATED: docs/skills.md

Update the `/implement` public skill description if it still advertises `2/2/3` or a HARD cap of 3.

### UPDATED: docs/collaborative-sketches.md

Update design plan-review prose so it no longer says escalation can authorize round 3.

### UPDATED: docs/review-agents.md

Update difficulty-tiered panel prose so HARD keeps the intended panel/model role differences but uses cap 2.

### UPDATED: docs/workflow-lifecycle.md

Update lifecycle prose that still says design, review, and implement use tier caps `2/2/3`.

## Edge cases

- Existing `difficulty-rating.json` files may contain `round_cap: 3`; the `_resolution_from_data` clamp ensures they resolve to 2 on the next read without rewriting the record.
- Escalation to HARD should still work for panel/model role purposes, but it must not unlock a third round.
- Historical fixtures under `python/test_fixtures/` may contain old prose. Do not edit them unless a targeted test requires fixture refresh.

## Failure modes

- A stale persisted cap can let resumed `/design` or `/implement` runs execute round 3 — mitigated by the `_resolution_from_data` clamp.
- Docs can contradict runtime behavior if only code changes — each file is a firm `### UPDATED:` target.
- Tests that count accepted findings may look like cap assertions. Update only true cap literals.

## Testing strategy

Run targeted tests:

- `python3 -m pytest python/tests/calibration/test_difficulty.py`
- `python3 -m pytest python/tests/calibration/test_difficulty_calibration.py`
- `python3 -m pytest python/tests/review/test_plan_review.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `make test-step3-review-cap`
- `make test-implement-review-token-propagation`

Run a final grep to confirm no stale cap-3 prose survives:

- `grep -RIn "2/2/3\|3-round cap\|HARD caps at 3\|HARD's 3-round cap\|cap of 3\|REVIEW_ROUND_CAP=3\|PANEL_ROUND_CAP=3\|EFFECTIVE_ROUND_CAP=3\|round 3" python/larch python/tests skills docs README.md`
- Confirm any remaining hits are historical fixtures or unrelated accepted-count fixtures.

## Acceptance

Run targeted tests:

- `python3 -m pytest python/tests/calibration/test_difficulty.py`
- `python3 -m pytest python/tests/calibration/test_difficulty_calibration.py`
- `python3 -m pytest python/tests/review/test_plan_review.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `make test-step3-review-cap`
- `make test-implement-review-token-propagation`

Run a final grep to confirm no stale cap-3 prose survives:

- `grep -RIn "2/2/3\|3-round cap\|HARD caps at 3\|HARD's 3-round cap\|cap of 3\|REVIEW_ROUND_CAP=3\|PANEL_ROUND_CAP=3\|EFFECTIVE_ROUND_CAP=3\|round 3" python/larch python/tests skills docs README.md`
- Confirm any remaining hits are historical fixtures or unrelated accepted-count fixtures.

diff_lines: 80

## Test plan
(no test plan section in plan-file)
