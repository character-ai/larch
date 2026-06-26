## Decision 1: Option choice
- **Question**: Option (a) fire in /implement or (b) document design-only?
- **Resolution**: Option (a) — make value-weighted pruning fire in /implement by lowering the activation round.
- **Source**: user

## Decision 2: Docs inconsistency
- **Question**: Fix docs/point-competition.md which says pruning is "unweighted" when code uses weighted_accepted_sum?
- **Resolution**: Yes, fix the docs wording to reflect value-weighted math.
- **Source**: user

## Decision 3: Activation round target
- **Question**: What round to activate at for /implement benefit?
- **Resolution**: Round 2 (change `round_num <= 2` to `round_num <= 1` in reviewer_prune_filter, and add "2" to prune_window_evaluated set). This is the earliest round with any ledger history.
- **Source**: codebase (implement rarely reaches round 3; round 2 is the practical target)

## Decision 4: Evidence requirement
- **Question**: Keep `len(recent) >= 2` or relax to allow round-2 pruning?
- **Resolution**: Change to `len(recent) >= 1`. Analysis confirms this has zero effect on rounds 3-4 (always 2 history entries there) and only enables pruning at round 2 where only 1 prior round exists. No destabilization of design.
- **Source**: codebase
