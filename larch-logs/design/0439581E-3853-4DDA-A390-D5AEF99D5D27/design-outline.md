## Proposed Design Outline

### Goals
- Replace the `accepted_count == 0` prune rule with a precision rule: prune a reviewer combo when, over its last 2 launched rounds, net score ≤ 0 OR acceptance rate < 1/3.
- Give the −1 reject penalty a live, in-loop consequence using the ledger already written.

### Non-goals
- No token-allocation weighting (stays "Future Plans").
- No change to the rounds 3–4 prune window, round-5 full re-probe, fail-open behavior, or the `LARCH_REVIEWER_PRUNE=off` knob.
- No new env knob; the 1/3 floor is a module constant.

### Approach sketch
- Add `rejected_count` and a total-findings count column to `reviewer-prune-ledger.tsv` (run-local, no migration).
- `reviewer_prune_record`: count rejected and total findings per combo from the classification TSV `voting_result`, alongside today's accepted count.
- `_ledger_history` + `reviewer_prune_filter`: aggregate the 3 counts over the last 2 rounds; prune when net score ≤ 0 OR acceptance rate < 1/3; still require ≥2 rounds of history.
- Update `docs/point-competition.md` "Conditional spawning" to describe the precision rule.

### Surfaces in scope
- `python/review_pipeline.py` (shared `reviewer_prune_*` functions; consumed by `/review` and `/design`).
- `reviewer-prune-ledger.tsv` header + writers/readers.
- `python/test_review_pipeline.py`; `python/test_plan_review_panel.py` ledger fixture.
- `docs/point-competition.md`.

### Open questions
- None.
