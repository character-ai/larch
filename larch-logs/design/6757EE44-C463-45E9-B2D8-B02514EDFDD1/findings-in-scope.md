### FINDING_1: Proposed/Findings denominator alias missing in voting-protocol.md
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `voting-protocol.md` update names only `Proposed` for the in-scope finding count while the scoreboard table header in the same section remains `Findings`. Future token-allocation readers who grep the scoreboard table for `Proposed` will not find it and may mis-bind the denominator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `voting-protocol.md` future-policy sentence, mirror the `point-competition.md` alias: `Findings` / `Proposed` (in-scope count)

### FINDING_2: Definition numerator uses tally-internal accepted_weight while scoreboard shows Accepted count
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned net-score-per-finding Definition pins the numerator to `accepted_weight − Rejected` while also claiming alignment with existing scoreboard columns. Live scoreboards (`python/plan_review_tally.py`, `python/review_tally.py`) print `Accepted` (count), `Rejected`, `Proposed`/`Findings`, and `Score`; they never expose `accepted_weight` as a column. Future token-allocation code or operators following the doc may compute `(Accepted − Rejected) ÷ Proposed` instead of the weighted numerator, understating reviewers with major/blocker accepts (+2) and breaking the stated precision-value goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Plan says net-score-per-finding is pinned to scoreboard columns, yet accepted_weight is tally-internal (python/plan_review_tally.py:684, python/review_tally.py:703); only Accepted, Rejected, Proposed/Findings, and Score are printed. A future allocator or operator can substitute (Accepted − Rejected) ÷ Proposed and ignore +2 major/blocker weighting whenever any accepted finding is blocker/major. In the Definition, give a column-visible form first: net-score-per-finding = (Score − OOS Accepted + OOS Rejected) ÷ Proposed/Findings (map Proposed in live voting-tally.md to Findings in docs/point-competition.md). State that accepted_weight − Rejected is equivalent but requires tally weighting or that derivation; warn explicitly that Accepted count is not accepted_weight.
  - From Cursor-Pragmatic: In the Definition, state explicitly that `Accepted` is a count, not the weighted numerator; define `accepted_weight` via `## Scoring Rules` (+2/+1). Optionally add the equivalent column-only form `(Score − OOS Accepted + OOS Rejected) ÷ Proposed`/`Findings` so the metric is derivable from displayed columns without tally internals.
```
