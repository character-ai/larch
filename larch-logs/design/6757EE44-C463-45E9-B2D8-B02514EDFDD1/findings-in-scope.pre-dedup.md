### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/voting-protocol.md:210-219
- **Concern**: Proposed `voting-protocol.md` update names only `Proposed` while the scoreboard table header in the same section remains `Findings`. Scenario: Future token-allocation readers grep the scoreboard table for `Proposed`, fail to find it, and mis-bind the denominator
- **Proposed resolution**: In the `voting-protocol.md` future-policy sentence, mirror the `point-competition.md` alias: `Findings` / `Proposed` (in-scope count)



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/point-competition.md:72-74
- **Concern**: skills/shared/voting-protocol.md:219. Scenario: Definition pins numerator to accepted_weight but scoreboard prints only Accepted count and Score
- **Proposed resolution**: Plan says net-score-per-finding is pinned to scoreboard columns, yet accepted_weight is tally-internal (python/plan_review_tally.py:684, python/review_tally.py:703); only Accepted, Rejected, Proposed/Findings, and Score are printed. A future allocator or operator can substitute (Accepted − Rejected) ÷ Proposed and ignore +2 major/blocker weighting whenever any accepted finding is blocker/major. In the Definition, give a column-visible form first: net-score-per-finding = (Score − OOS Accepted + OOS Rejected) ÷ Proposed/Findings (map Proposed in live voting-tally.md to Findings in docs/point-competition.md). State that accepted_weight − Rejected is equivalent but requires tally weighting or that derivation; warn explicitly that Accepted count is not accepted_weight.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/point-competition.md:Future Plans Definition
- **Concern**: The Definition pins the numerator to `accepted_weight − Rejected` while also saying it is pinned to existing scoreboard columns, but live scoreboards (`python/plan_review_tally.py`, `python/review_tally.py`) expose `Accepted` (count), `Rejected`, `Proposed`/`Findings`, and `Score`; they never expose `accepted_weight` as a column.. Scenario: Future token-allocation code or operators following the doc may compute `(Accepted − Rejected) ÷ Proposed` instead of the weighted numerator, understating reviewers with major/blocker accepts (+2) and breaking the stated precision-value goal.
- **Proposed resolution**: In the Definition, state explicitly that `Accepted` is a count, not the weighted numerator; define `accepted_weight` via `## Scoring Rules` (+2/+1). Optionally add the equivalent column-only form `(Score − OOS Accepted + OOS Rejected) ÷ Proposed`/`Findings` so the metric is derivable from displayed columns without tally internals.



