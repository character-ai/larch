## Decision 1: Tier rule (severity source + boundary)
- **Question**: How is the +2 high tier determined? Which severity field, and which severities qualify?
- **Resolution**: Use **panel-assessed severity** (the voting panel's per-voter `vN_severity` consensus, not the reviewer-declared `body_severity`) so reviewers cannot inflate their own score. Two tiers only: `blocker` and `major` → **+2**; `minor`, `nit`, `uncertain` → **+1**.
- **Source**: user

## Decision 2: Penalty symmetry
- **Question**: Today a rejected finding is a flat -1. Scale the penalty symmetrically with severity?
- **Resolution**: **Keep the penalty flat at -1.** Weight only the positive reward (+2/+1). Rejected stays -1 regardless of severity. Rationale: panel-assessed severity already removes any inflation incentive, and a flat penalty avoids discouraging reviewers from attempting hard, high-value findings (the issue's stated goal).
- **Source**: user

## Decision 3: Conditional-spawning pruning interaction
- **Question**: Rounds-3-4 pruning uses net score = accepted − rejected (unweighted counts). Should severity weights feed that pruning threshold?
- **Resolution**: **Out of scope.** Pruning keeps its current unweighted accepted-minus-rejected count math; no threshold retuning. Severity weighting changes only the visible competition scoreboard/score.
- **Source**: user

## Decision 4: OOS finding weighting
- **Question**: Do out-of-scope (OOS) observations get the same two-tier weighting?
- **Resolution**: **No — OOS stays flat (+1 accepted / -1 rejected).** OOS rows carry no severity: the findings-classification header has `body_severity` only for in-scope findings, and `progress_report.py` skips `OOS_*` rows in attribution. Weighting OOS is undefined, so the flat OOS shape is preserved unchanged.
- **Source**: codebase

## Decision 5: Dependency on #4764 (self-contained scope)
- **Question**: #4773's body lists #4764 ("shared scoreboard + findings-classification.tsv surface") as a dependency/conflict. Does this block the design?
- **Resolution**: **No blocking dependency.** #4764 is actually "[DONE] Strip author attribution from voting ballots" — already merged. The severity data needed for weighting already exists today as a per-round runtime artifact `findings-classification.tsv` (`progress_report.py` reads `round_dir/findings-classification.tsv`) carrying per-voter `vN_severity` and `body_severity`. The design is **self-contained on current surfaces** (`python/voting.py`, `python/progress_report.py`, `python/review_pipeline.py`, `skills/shared/voting-protocol.md`, `docs/point-competition.md`).
- **Source**: codebase

## Hard constraints / must-not-break (carried into plan)
- Preserve the existing flat OOS score shape and the conditional-spawning net-score (unweighted) pruning math.
- Preserve dedup behavior: all contributing reviewers of a merged finding receive the same (now weighted) points.
- Keep it two tiers — "not a baroque table" (explicit issue constraint).
- Weighting applies wherever competition scoring runs (`/design` plan review and `/review` code review), consistent with `docs/point-competition.md` "Where Scoring Applies".
