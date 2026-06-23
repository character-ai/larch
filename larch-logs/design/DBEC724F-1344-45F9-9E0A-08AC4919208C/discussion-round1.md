## Decision 1: Threshold configurability
- **Question**: Should the >90% high-severity "uncalibrated" threshold be configurable?
- **Resolution**: Configurable. Add `--high-severity-threshold` flag to voter-calibration.py (default 0.90) and a `high_severity_threshold` keyword param on `compute_voter_severity_distribution` (default 0.90). Mirrors `--outlier-threshold` / `outlier_threshold` pattern.
- **Source**: user

## Decision 2: Tally placement
- **Question**: Where should the severity scoreboard appear in live tally output?
- **Resolution**: Appended immediately after the existing agreement scoreboard in both review_tally.py and plan_review_tally.py. Same render pattern; one extra table per tally output.
- **Source**: user

## Decision 3: "High" severity definition
- **Question**: What counts as "high" severity?
- **Resolution**: Reuse existing `HIGH_SEVERITIES = frozenset({JudgeSeverity.blocker.value, JudgeSeverity.major.value})`. No new definition needed.
- **Source**: codebase

## Decision 4: Diagnostics-only constraint
- **Question**: Does this change affect any live voting decisions?
- **Resolution**: No. The issue is explicit: "do not wire the signal into any live decision until severity spread is real and stable." This is display/report only.
- **Source**: codebase (issue body)

## Decision 5: Backward compatibility
- **Question**: Must existing function signatures and column format remain unchanged?
- **Resolution**: Yes. `compute_voter_agreement`, `render_voter_scoreboard`, and the tally column layout must not change. All new capability is additive.
- **Source**: codebase ("No behavior change by design")
