## Decision 1: Item A reconciliation direction
- **Question**: For research-phase.md / validation-phase.md paired-PID prose conflict, which reconciliation direction?
- **Resolution**: Update prose to background+monitor — preserves paired-PID timeout semantics and live breadcrumbs (matches /design, /implement convention).
- **Source**: user

## Decision 2: Item B audit scope
- **Question**: How wide should the audit for defensive `unset LARCH_PAIRED_PID_FILE` go?
- **Resolution**: Full sweep — audit ALL callers of `dispatch-with-waterfall.sh` and add `unset` where missing. Plus the linter extension and `lint-foreground-markers.md` update.
- **Source**: user

## Decision 3: Item C scope
- **Question**: For the dual vendor slots + per-slot waterfall doubling Codex work, what is the scope?
- **Resolution**: Define + implement dedup logic — single-PR end-to-end fix (contract prose + coordination implementation).
- **Source**: user

## Decision 4: Callers requiring defensive `unset LARCH_PAIRED_PID_FILE`
- **Question**: Which existing callers of `dispatch-with-waterfall.sh` are missing the defensive `unset`?
- **Resolution**: Codebase grep enumerates these callers. Already have `unset`: `scripts/dispatch-code-voters.sh:172`, `scripts/dispatch-plan-voters.sh:140`. Missing `unset` (must be added): `skills/design/scripts/dispatch-plan-review-panel.sh` (the named offender), `skills/design/scripts/decompose-panel-dispatch.sh`, `skills/design/scripts/decompose-aggregator.sh`, `skills/review/scripts/aggregate-findings.sh`, `skills/review/scripts/dispatch-panel.sh`.
- **Source**: codebase

## Decision 5: In-scope vs. out-of-scope
- **Question**: Are there related changes the user does NOT want in this issue?
- **Resolution**: In-scope = Items A (prose update), B (defensive `unset` sweep + linter rule + `lint-foreground-markers.md` doc update), C (dedup contract + implementation). Out-of-scope = redesigning the paired-PID mechanism itself, expanding the Family B denylist, changing the existing top-level Family B writer set.
- **Source**: user (Step 1c maximalist option choices)

## Decision 6: Hard constraints (must not break)
- **Question**: What must not break?
- **Resolution**: Existing background+monitor contract (BASH_AUTHORING.md §4) must remain authoritative. Existing paired-PID semantics for top-level Family B writers (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`, `dispatch-plan-voters.sh`) must remain intact. `lint-foreground-markers.sh` must continue to pass on all existing fences. All existing tests under `scripts/test-*.sh` must continue to pass.
- **Source**: codebase
