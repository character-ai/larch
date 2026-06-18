## Proposed Design Outline

### Goals
- Replace the hardcoded `--accepted 0 --rejected 0` in SKILL.md's self-review tally fence with real counts.
- Make `code-review-tally.json` and `final-summary.md` reflect actual self-review findings applied and rejected.
- Add a regression test confirming the tally receives non-zero counts when fixes were applied.

### Non-goals
- Populating `review-findings-full.jsonl` with structured finding entries (tally-only fix; JSONL stays as an empty sentinel).
- Changes to the external (panel) review path or `write_self_review_tally()` Python internals.
- Changes to `audit-runs` or `fluff-analysis` consumers (they already read `accepted_count`/`rejected_count` correctly).

### Approach sketch
- Instruct the SKILL.md self-review flow to track `_self_review_accepted` as inline fixes are applied in step 4.
- After step 5, count `### [Code Review] Self-review` entries in `rejected-findings.md` via a Bash probe for `_self_review_rejected`.
- Replace the step 9 fence literal with the computed counts.
- Update `docs/run-logs.md` to document that `mode: self-review` reports real applied/rejected counts.
- Add a regression test in `python/test_review_and_fix.py`.

### Surfaces in scope
- `skills/implement/SKILL.md` — self-review step 4 (counter tracking) and step 9 (tally fence).
- `docs/run-logs.md` — `mode: self-review` semantics.
- `python/test_review_and_fix.py` — new regression test for `write_self_review_tally` with non-zero counts.

### Open questions
- None.
