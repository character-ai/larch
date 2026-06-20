## Decision 1: Precision-value signal
- **Question**: Which precision-value signal should the revised policy name as the basis for token allocation (acceptance rate, net-score-per-finding, or precision × mean-accepted-value)?
- **Resolution**: Net-score-per-finding — the existing ± competition points (Σ(accepted − rejected), with +2 for major/blocker) divided by the reviewer's finding count. Removes the volume reward, keeps severity weighting, reuses today's scoring.
- **Source**: user

## Decision 2: Documentation depth
- **Question**: How much should this change write into the docs, given token allocation is still a "Future Plans" item (not yet implemented)?
- **Resolution**: Reword both Future Plans statements to "by precision-value, not cumulative score", and add a short rationale subsection (precision-vs-volume with the worked example) in `docs/point-competition.md`. Not a full implementation-ready formula spec.
- **Source**: user

## Decision 3: Dependency preconditions
- **Question**: Should the revised policy state the issue's two dependencies as preconditions?
- **Resolution**: Yes — state that token allocation must not ship until (a) value-weighted points define "value" and (b) voter calibration validates the signal. Matches the issue's "Depends on".
- **Source**: user

## Decision 4: Scope boundary (docs-only)
- **Question**: Does any token-allocation code exist that must change?
- **Resolution**: No. Grep of `python/` and `scripts/` found no token-allocation implementation; token allocation is described only as a future plan. This change is documentation-only.
- **Source**: codebase

## Decision 5: Hard constraints / non-goals
- **Question**: What must not change?
- **Resolution**: Do not alter the scoring tables, the scoreboard schema, or the +2/+1/−1 competition point rules. Preserve the readability precision contract (byte-stable code spans, tables, identifiers). Do not modify the two diagnostic "unchanged" mentions (`docs/voting-process.md` Voter Agreement Scoreboard; `skills/voter-calibration/SKILL.md`) — they state what diagnostics do not touch, not how allocation works. Do not implement token allocation.
- **Source**: codebase
