## Decision 1: Treatment of stale #2667 plan body
- **Question**: PR #3142 (today) integrated Piece 2 as INT-2871 with different artifact names than #2667 predicted. Should this design follow the stale plan literally or rederive the actual gap?
- **Resolution**: Rederive actual gap. Treat the #2667 body as historical background; inspect the currently landed code and produce a narrow accurate docs-reconciliation plan. Items already done are dropped; items still missing are added; names match landed artifacts.
- **Source**: user

## Decision 2: Gate C re-review copy reconciliation
- **Question**: The original plan offered two options: (a) amend Gate C copy to describe cumulative-audit + fresh-panel-output coexistence, or (b) explicitly reset cumulative artifacts on Gate C re-run. Resolve in design?
- **Resolution**: Deferred to codebase inspection. Inspection shows: `oos-accepted-design.md` accumulates WITHIN a single multi-round loop via `_accumulate_round_oos` in `plan-review-loop.sh`, but Step 3 re-entry from Gate C(c) starts a fresh loop that overwrites `oos-accepted-design.md` (no cross-run preservation). Current `approval-gates.md` Gate C copy already says "Findings from prior review runs are NOT preserved — each review is a fresh look at the latest plan", which is correct as written. The new docs add WITHIN-loop cumulation prose to `plan-review.md` rather than changing Gate C copy.
- **Source**: codebase

## Decision 3: Tokens from the stale plan that don't exist in landed code
- **Question**: Should the new plan reference `applied-plan-findings.md`, `MAIN_AGENT_VOTE_REQUIRED_DEFERRED`, `lib-voter-coverage.sh`, `LARCH_DESIGN_VOTER_COVERAGE_FRACTION`, `plan-review-rounds-summary.md` from the stale #2667 plan?
- **Resolution**: No. None of these landed. Drop entirely. Use actual landed names: `accepted-plan-findings.md` (final-round at session root, cumulative-within-loop via the per-round `plan-review/round-<N>/` subtree), `round-summary.env` (per-round, not a single cumulative summary file), `oos-accepted-design.md` (cumulative-within-loop), `plan-review-loop.sh` env vars `LARCH_DESIGN_CONVERGENCE_THRESHOLD` and `LARCH_DESIGN_ROUND_CAP` only.
- **Source**: codebase

## Decision 4: Removal of TALLY_PLAN_REVIEW_STATUS / VOTER_1_PATH references from SKILL.md Step 3
- **Question**: Original plan called for a final SKILL.md Step 3 sweep removing these tokens.
- **Resolution**: No. Inspection shows both tokens are load-bearing in the current loop-driver wiring (`TALLY_PLAN_REVIEW_STATUS` is parsed from `plan-review-loop.sh` stdout to detect tally errors and route to Step 3b without false convergence; `VOTER_1_PARSE_RATE_STATUS` is similar). Skip the sweep directive from the original plan.
- **Source**: codebase

## Decision 5: Scope of structure-test assertions
- **Question**: Original plan called for 3 structure-test assertions including a `MAIN_AGENT_VOTE_REQUIRED_DEFERRED` Gate B reorder check.
- **Resolution**: Drop the deferred-vote ordering check (the token doesn't exist). Add 2 assertions: severity-precedence prose in approval-gates.md, and FINDING_N template fields in plan-review.md. The third "approval-gates.md:5 rewrite" is moot — the line-5 sentence is already different from the original plan's predicted text.
- **Source**: codebase
