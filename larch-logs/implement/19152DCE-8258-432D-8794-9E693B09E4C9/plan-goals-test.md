## Goal
Implement issue #5730: [IMPLEMENTING] [BUG] Restore reviewer-prune activation to round 3 (revert round-2 pruning from #5463).

## Implementation Plan
## Summary

Revert the round-2 reviewer-prune activation introduced by #5463 (PR #5526) so first-pruning starts at **round 3** again, for **both** `/implement` code review and `/design` plan review. Targeted mitigation, not the full fix.

## Affects both /implement and /design

The reviewer-prune machinery is shared. #5463 moved first-pruning from round 3 to round 2 in shared code **and** rewired the design path to follow it:

- Shared `reviewer_prune_filter` (`python/larch/review/review_pipeline.py`): guard `round_num <= 2` to `round_num <= 1`; added `min_recent = 1 if round_num == 2 else 2`; `len(recent) >= 2` to `>= min_recent`. (Used directly by `/implement` Step 5 code review.)
- Shared `prune_window_evaluated` (`python/larch/review/review_pipeline.py`): `{"3","4"}` to `{"2","3","4"}`.
- `/design` plan-review `_filter_pruned` (`python/larch/review/plan_review_panel.py`): gate changed from `prune_round_num not in {3, 4}` to `prune_window_evaluated(prune_round_num) != "true"`. So plan review now prunes at rounds 2-4 too.

## Why it matters (the trigger)

This amplifier turned a separate latent defect into a visible failure. In `/implement` run `F6070E45` (PR #5724, issue #5642), round 1 ran the full 11-slot panel and accepted 10 findings, but **round 2 launched 0 reviewers**: all 11 combos were pruned (`round-2/prune-decision.env`: `PANEL_PRUNED_EMPTY=true`, `PRUNED_COUNT=11`; `round-2/voting-tally.md`: "Round skipped: all reviewer combos pruned"). The round-1 prune ledger had recorded all-zero productivity, so with `min_recent=1` every combo satisfied the `weighted_accepted - rejected <= 0` prune test at round 2.

Restoring round-3 activation (require two prior rounds of evidence) means a single bad ledger round can no longer wipe the entire panel, in either skill.

## Scope of change (the revert)

- `reviewer_prune_filter`: change the skip guard `round_num <= 1` back to `round_num <= 2`; revert `min_recent` so pruning requires `len(recent) >= 2`. Keep `round_num >= 5` unchanged.
- `prune_window_evaluated`: `{"2","3","4"}` back to `{"3","4"}`. This single revert restores the `/design` `_filter_pruned` gate to rounds 3-4 with no further edit in `plan_review_panel.py`, since that gate delegates to this function.
- Prose: ensure rounds-3-4 wording in the implement Step 5 banner (`skills/implement/scripts/step-5-review.sh`), `skills/implement/SKILL.md`, `docs/point-competition.md`, and `docs/configuration-and-permissions.md`. Note: `skills/design/references/plan-review.md` already says "rounds 3-4" (it was never updated to 2-4 by #5463), so it becomes correct again after the revert. Verify, do not rewrite.
- Tests: revert/adjust the round-gate expectations added by #5463 in `python/test_review_pipeline.py` and `python/test_plan_review_panel.py`.

## Acceptance criteria

- Round 2 of both `/implement` code review and `/design` plan review always runs the full eligible reviewer panel (no pruning).
- Reviewer-prune can only drop combos at round 3 or 4, in both skills.
- Round-gate prose and tests consistently say rounds 3-4.

## Note

This only removes the amplifier. The underlying defect (round-1 prune ledger recording all-zero reviewer productivity due to a slot-label join-key mismatch between bare classification tokens and the `-output.txt` manifest filename key) is tracked separately and is what actually makes pruning compute wrong. The code-review join path (`plan_mode=False`) is confirmed broken; whether the design plan-review join (`plan_mode=True`, via the label map) is also broken is unverified. Restoring round-3 just limits the blast radius.

## Test plan
(no test plan section in plan-file)
