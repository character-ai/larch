## Proposed Design Outline

### Goals
- Anchor `/design` plan-review **scout, reviewers, and voters** to the originating issue so over-scoped plans are visible and flaggable.
- Break the one-way ratchet: let a scope-reduction finding **win** against additions instead of being structurally outvoted.
- Ship regression coverage proving a scope-cut finding can win against an over-scoped plan.

### Non-goals
- No Gate B auto-apply / drift-convergence change (loop-dynamics sibling issue).
- No plan-quality-assessor-on-SIMPLE change (other sibling issue).
- No behavior change for `/research`, `/review`, `/implement` voters — shared `render-voter-prompt.sh` stays backward-compatible.

### Approach sketch
- **Reviewer** (`render-plan-review-prompt.sh`): inject the issue anchor + the original pre-review plan baseline; task reviewers to flag over-scope relative to the issue.
- **Voter** (`render-voter-prompt.sh`, shared): add an optional plan-review-only scope-anchor injection; re-anchor the EXONERATE proportionality test to "more complex than **the issue** warrants".
- **Tally** (`lib-vote-tally.sh` / `tally-plan-review.sh`): give scope-reduction findings a protected class that additions cannot structurally outvote (both tiers, uniform).
- **Ballot/context** (`plan-review-loop.sh`): feed the issue anchor into the ballot + reviewer/scout context.
- **Scout** (`scout-plan-archetypes-wrapper.sh` + prompt): derive archetypes from the issue/outline, not the drifting plan.

### Surfaces in scope
- `skills/design/scripts/render-plan-review-prompt.sh`, `scout-plan-archetypes-wrapper.sh` (+ `scout-plan-archetypes-prompt.txt`), `plan-review-loop.sh`, `tally-plan-review.sh`
- `skills/shared/scripts/render-voter-prompt.sh`, `scripts/dispatch-plan-voters.sh`, `scripts/lib-vote-tally.sh`
- Harnesses + new scope-reduction regression test; `make lint` green

### Open questions
- How a scope-reduction finding is classified for the protected class (new TSV scope value vs. focus_area vs. detection rule) — resolved in the plan, kept minimal.
