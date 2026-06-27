## Proposed Design Outline

### Goals
- Route neutral findings (1 YES, blocker/major severity) to `oos.md` with a `(neutral-rescued)` label instead of the rejected file.
- Apply consistently to both code-review (`review_tally.py`) and plan-review (`plan_review_tally.py`) tally paths.
- Exclude rescued neutrals from `NEUTRAL_COUNT`/`REJECTED_COUNT`; reflect them in `OOS_REJECTED_COUNT` only.

### Non-goals
- Changing the 2-YES acceptance threshold for inline accepted findings.
- Rescuing minor/nit-endorsed neutral findings (stay dropped to avoid OOS spam).
- Adding tally-level OOS dedup (handled downstream by `oos_filer.py`).
- Changes to `oos_filer.py`, `voting.py`, or the `HIGH_SEVERITIES` constant (already correct).

### Approach sketch
- In `review_tally.py` `tally_code_votes`: compute `neutral_rescued` (result=="neutral" and any YES cell with severity in HIGH_SEVERITIES) before `_record_classification_and_ledger`, use it in ledger outcome ("oos"), and add a branch that writes to `oos_file` with "(neutral-rescued)" suffix.
- In `plan_review_tally.py` `_render`: add the same neutral-rescued branch after the latent-rerouted branch; in `_write_findings_ledger`: apply the same outcome="oos" substitution for neutral-rescued items.
- Add helper `_is_neutral_rescued(result, votes, severities)` to avoid inline `any(...)` duplication across `_render` and `_write_findings_ledger`.
- Document the neutral-rescue rule in `skills/shared/review-acceptance-rubric.md`.

### Surfaces in scope
- `python/larch/review/review_tally.py`
- `python/larch/review/plan_review_tally.py`
- `python/test_review_tally.py`
- `python/test_plan_review.py`
- `skills/shared/review-acceptance-rubric.md`

### Open questions
- None.
