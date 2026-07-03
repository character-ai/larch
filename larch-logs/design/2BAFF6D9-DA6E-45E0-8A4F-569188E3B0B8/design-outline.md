## Proposed Design Outline

### Goals
- Fix `plan_review_tally.py` so `accepted-plan-findings-all.md` and `oos-accepted-design.md` actually cumulate (union of all rounds) across automatic continuation rounds within one Step 3 loop, instead of only ever reflecting the current round.
- Implement the accumulation contract already documented in `plan-review.md` (`_accumulate_round_accepted_all`, `_accumulate_round_oos`, or functional equivalents), so the doc and the code agree.
- Add regression test coverage that exercises real multi-round accumulation: round 1 finds N accepted findings/OOS items, round 2 finds zero, and the cumulative files still hold round 1's content afterward.

### Non-goals
- Do not cumulate `rejected-findings.md` or `oos.md` (the non-accepted, per-round variants) — scoped out in Round 1 Decision 1.
- Do not add the Step 5b defense-in-depth empty-file warning from suggested-fix #4 — scoped out in Round 1 Decision 2.
- Do not change the existing delete-on-manual-reentry cleanup behavior for these files during Gate A/C manual re-entry (`plan_review_loop.py`'s `direct_review_entry` branch) — cumulation applies only within one continuous automatic-continuation loop, not across manual re-entries.

### Approach sketch
- In `plan_review_tally.py`, before the per-round content is finalized, snapshot existing on-disk `oos-accepted-design.md` content so it survives the unconditional blank at lines 664-669.
- After `_render(...)` produces the current round's OOS/accepted-findings content, merge the prior snapshot with the current round's content (union, not overwrite) and write the combined result back to `oos-accepted-design.md` and `accepted-plan-findings-all.md`.
- First-round behavior (no prior snapshot) reduces to today's current-round-only content, so single-round runs are unaffected.
- Leave `accepted-plan-findings.md`, `rejected-findings.md`, and `oos.md` (the per-round-only files) as unconditional per-round writes, unchanged.

### Surfaces in scope
- `python/larch/review/plan_review_tally.py` — primary fix site (accumulate-before/after-blank).
- `python/larch/review/plan_review_loop.py` — round orchestration; touched only if accumulation is cleaner to own at the loop level rather than inside tally.
- `python/tests/review/test_plan_review.py` — new multi-round accumulation regression coverage.
- `skills/design/references/plan-review.md` — verify the documented contract matches the implemented behavior once done.

### Open questions
- None.
