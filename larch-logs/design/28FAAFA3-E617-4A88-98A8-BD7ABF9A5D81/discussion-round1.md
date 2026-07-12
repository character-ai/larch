# Discussion Round 1 — Resolved Decisions

## Decision 1: Issue scope — plan_grammar parsers only
- **Question**: Are the three adjacent marker-drift sites (decompose.py inline marker composition, learn_from_bugs.py case-insensitive marker regex, design_router.py literal marker checks) in-scope, or only the six heading/trailer parsers?
- **Resolution**: In-scope = repoint the six heading/trailer parser sites to `plan_grammar.py`. The three marker-drift sites are OUT of scope for this issue. If no existing issues cover them, file follow-up issue(s) as appropriate (handled via the OOS pipeline / `/larch:issue` at Step 5b).
- **Source**: user

## Decision 2: Heading-form unification direction — preserve union
- **Question**: Unify the diverged heading regexes to strict `^###` four-heading, or preserve the union of accepted forms?
- **Resolution**: Preserve the union — the single owner regex accepts `^#{2,3}`, all four headings (NEW/UPDATED/REWRITTEN/MAY_UPDATE), and the bracket form. No currently-parsing plan may be rejected. Backward-compatible refactor.
- **Source**: user

## Decision 3: Trailer key ownership boundary — full set in plan_grammar
- **Question**: Does `plan_grammar.py` own the complete trailer key set (difficulty, diff_lines, diff_added, diff_deleted, mechanical_churn, oversize_override), or only size/diff trailers?
- **Resolution**: `plan_grammar` owns ALL trailer keys as the single source of truth; `calibration/difficulty.py` repoints its regex to `plan_grammar`. "Adding a trailer key = one-file change" is the done criterion.
- **Source**: user

## Hard constraints (must not break)
- No currently-accepted plan heading or trailer may become unparseable after unification (backward compatibility is mandatory).
- `issue_wire` remains the marker owner; `plan_grammar` owns heading/trailer grammar only, not markers.
- `docs/issue-anchored-plan.md` must name `plan_grammar` as the normative plan-format owner.

## Non-goals (out of scope — file follow-ups if no issue exists)
- `design/decompose.py` inline marker composition → `issue_wire.compose_named_block`.
- `learn_from_bugs.py` case-insensitive marker regex normalization.
- `design_router.py` literal marker check normalization.
