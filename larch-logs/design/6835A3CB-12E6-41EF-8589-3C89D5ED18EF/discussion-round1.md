# Discussion Round 1 — Issue #3619

## Decision 1: Ratchet policy (re-probe vs no-redemption)
- **Question**: Should a pruned combo ever return within a run (the issue's open "no-redemption ratchet" question)?
- **Resolution**: Rounds 1-2 spawn all combos. Rounds 3-4 prune. Round 5 spawns ALL reviewers again (full re-probe): reaching round 5 means convergence failed, the situation is hard, and more reviewers may help.
- **Source**: user

## Decision 2: Empty-panel round
- **Question**: What happens when EVERY combo would be pruned for a round?
- **Resolution**: Skip the round entirely — spawn nothing, print a breadcrumb, treat the round as zero-findings (convergence signal). Maximum token savings.
- **Source**: user

## Decision 3: Non-launched rounds and the 2-round window
- **Question**: Do rounds where a combo was not launched (fresh dynamic archetypes, tool outages) count toward its pruning window?
- **Resolution**: No. A combo is pruned only after 2 launched-and-collected rounds with zero accepted items. Combos with fewer than 2 such rounds of history always launch (clean slate). Rounds where the combo launched but its output failed collection (collector status not OK) do not count against it.
- **Source**: user (launched-rounds-only option; collection-failure refinement follows the same "never got a chance" intent)

## Decision 4: Hard round cap at 5 — no cap expansion
- **Question**: What happens on rounds 6+ (today only reachable in /implement via degraded-round cap inflation)?
- **Resolution**: Rounds are hard-capped at 5 everywhere. Remove the /implement degraded-round cap-inflation mechanism (`ROUND_CAP_INFLATED = ROUND_CAP_BASE + DEGRADED_ROUNDS`) so no round past 5 ever runs. Rounds 6+ become unreachable; no policy needed for them.
- **Source**: user

## Decision 5: Escape hatch
- **Question**: Env-var escape hatch to disable conditional spawning?
- **Resolution**: Yes. One env var restores unconditional full-panel spawning for debugging and A/B cost measurement via /report-tokens.
- **Source**: user

## Decision 6: Definition of "accepted suggestion"
- **Question**: Which vote outcomes mark a combo productive?
- **Resolution**: `voting_result=accepted` rows in the round's findings-classification TSV, including accepted OOS rows (both score +1 in the point competition). Neutral (≥1 YES, not accepted) does not count.
- **Source**: codebase (issue text "a voted-in finding"; docs/point-competition.md scoring)

## Decision 7: Pruning applies to finding-producing reviewers only
- **Question**: Are voters/judges or the dynamic-archetype scout affected?
- **Resolution**: No. Only reviewer slots that produce findings are pruned. Voter panels, judge panels, and the scout are untouched.
- **Source**: codebase (issue text: "did not produce any accepted suggestion" — only reviewers produce suggestions)

## Decision 8: State scope
- **Question**: Does combo performance persist across runs?
- **Resolution**: No. Rounds exist only within one run (/design Gate C re-entries in one DESIGN_TMPDIR; /implement Step 5 rounds in one IMPLEMENT_TMPDIR; /review rounds in one REVIEW_TMPDIR). Pruning state is derived per run from per-round artifacts already on disk.
- **Source**: codebase
