## Decision 1: Voter change invasiveness
- **Question**: How invasive should the plan-review scope fix be, given render-voter-prompt.sh is shared across /research, /review, /implement?
- **Resolution**: Beyond anchoring the voter to the issue + re-anchoring the proportionality test, ALSO add a structural protection so scope-reduction findings cannot be outvoted by additions (tally-machinery change). Shared voter prompt must stay backward-compatible (plan-review-only injection).
- **Source**: user

## Decision 2: Scout re-anchoring
- **Question**: How should the scout avoid specializing into plan bloat?
- **Resolution**: Re-anchor the scout to derive dynamic archetypes primarily from the originating issue + approved outline, not the drifting plan body. (Not "freeze to round 1".)
- **Source**: user

## Decision 3: Reviewer drift baseline
- **Question**: Should reviewers receive the original pre-review plan as a baseline?
- **Resolution**: Yes. Pass reviewers the issue anchor AND the original pre-review plan (plan.txt-original snapshot) so cumulative drift / over-scope is explicit and flaggable.
- **Source**: user

## Decision 4: Sibling-issue scope boundary
- **Question**: Do the two sibling concerns (loop dynamics: no auto-apply + drift convergence; assessor-on-SIMPLE) stay out of scope?
- **Resolution**: Yes — OUT of scope. This issue only anchors scout/reviewer/voter (and the ballot) to the issue and adds regression coverage. No changes to Gate B auto-apply/convergence or assessor-on-SIMPLE.
- **Source**: user

## Decision 5: Tier applicability
- **Question**: Apply the issue-anchoring + protected scope-cut class to both SIMPLE and HARD, or SIMPLE only?
- **Resolution**: Both tiers, uniform. No tier-conditional tally branching. The issue anchor is context; the scope-cut protection prevents the one-way ratchet regardless of tier.
- **Source**: user
