## Decision 1: Dependency — value-weighted points base (#4773)
- **Question**: Is the "value-weighted points" base (#4773) landed, so #4774 is unblocked?
- **Resolution**: Yes. #4773 is CLOSED/DONE (PR #4904, released v51.3.0). Current code already has severity-weighted accepted points (+2 blocker/major, +1 other) via `voting.accepted_finding_points_from_severities`. #4774 is unblocked and is designed against the current scheme.
- **Source**: codebase

## Decision 2: Pricing mechanism
- **Question**: How to price a non-accepted (neutral) finding so it costs more than silence (0)?
- **Resolution**: Set neutral = −0.25 (neutral-only negative). Accepted (+2/+1), rejected (−1), and silence (0) are unchanged. Preserves ordering rejected(−1) < neutral(−0.25) < silence(0) < accepted(+1/+2). NOT a flat per-finding submission cost.
- **Source**: user

## Decision 3: Surface scope (which scoreboards)
- **Question**: Which review scoreboards get the new neutral pricing?
- **Resolution**: Both /design (`python/plan_review_tally.py`) and /review (`python/review_tally.py`), plus the shared `voting.py` scoreboard CLI path, so the two skills stay consistent. The issue's "Affected surfaces" named only `python/voting.py`; the live score math is duplicated in the two tally modules.
- **Source**: user

## Decision 4: OOS neutral
- **Question**: Apply the neutral cost to out-of-scope (OOS) neutral items too?
- **Resolution**: In-scope neutral only. OOS neutral stays at 0. Leave OOS scoring changes to #4776.
- **Source**: user

## Non-goals / hard constraints
- Do NOT change rejected (−1), accepted (+2/+1), or silence (0).
- Do NOT change OOS scoring: OOS neutral stays 0; OOS accepted (+1) and OOS rejected (−1) unchanged.
- Do NOT wire the neutral cost into conditional reviewer pruning (that is #4772; pruning math stays unweighted accepted-minus-rejected counts).
- Do NOT change precision-based token allocation / Top reviewers in `python/progress_report.py` (that is #4771; it sums accepted in-scope points only).
- Do NOT change the run-log tally `--neutral` argument semantics in `voting.py` (`compose_tally_record`): it is a finding COUNT, not a point value, and stays a non-negative integer.
- Fractional scores are accepted (neutral −0.25 makes per-reviewer Score columns potentially non-integer).
