## Decision 1: Overall approach — consistency + test pass (not assessor rework)
- **Question**: Given gap 1's passive-summary→Step 3.6 routing already exists in both SKILL.md and approval-gates.md, how should the plan treat the three gaps?
- **Resolution**: Treat gaps 1-2 as making Step 3.6 routing EXPLICIT and CONSISTENT across SKILL.md ↔ approval-gates.md. Do NOT rework `assess-plan-round.sh` / `snapshot-plan-round.sh` mechanics (round<2 skip, missing-snapshot, degraded-default-open all stay as-is). Gap 3 is the real net-new coverage.
- **Source**: user

## Decision 2: Short-circuit Step 3.6 behavior — explicit skip + breadcrumb
- **Question**: For Step 3 short-circuit exits (panel-failed, tally-error, cap-reached) on HARD runs, should Step 3.6 be explicitly skipped or routed through?
- **Resolution**: Explicitly SKIP Step 3.6 on those paths with a visible breadcrumb (no clean new review round ⇒ round-over-round assessor has nothing valid to compare). Align both docs, including adding `panel-failed` to approval-gates.md's existing "skip Gate B (and therefore Step 3.6)" enumeration.
- **Source**: user

## Decision 3: Gap-3 test form — expand test-assess-plan-round.sh
- **Question**: New harness vs expand the existing test for the cursor-advance → Gate B settle → write-after → second Step 3 entry flow?
- **Resolution**: Expand the existing `skills/design/scripts/test-assess-plan-round.sh` (292 lines) with an end-to-end integration case. No new test file or Makefile target.
- **Source**: user

## Hard constraints (must not break) — codebase-derived
- `assess-plan-round.sh` behavior is unchanged: HARD-only, skip when `ROUND_NUM < 2`, `missing-snapshot` skip, `degraded-default-open` default-open on 0 effective assessors. The assessor only does real work on the SECOND review run onward.
- `zero-findings-degraded-panel` and Gate B's zero-findings short-circuit must KEEP routing THROUGH Step 3.6 (approval-gates.md zero-findings short-circuit) — they are NOT added to any skip list. Only `panel-failed`/`tally-error`/`cap-reached` (and the already-listed `degraded-empty-collector`) skip 3.6.
- The `LOOP_STATUS` validation enum (SKILL.md Step 3 regex) must remain valid; no new status tokens introduced.
- Structural pins must still pass: `scripts/test-design-structure.sh` (SKILL.md anchors), markdownlint (MD038/MD001), `make lint-bash32`, and the offline assessor harnesses.
- SIMPLE tier behavior is untouched (assessor always skips on SIMPLE via `workflow_path != HARD`); breadcrumb/routing changes are HARD-relevant and must not regress SIMPLE.

## Non-goals
- No rework of assessor scoring, dispatch, or tally mechanics.
- No new test harness file or Makefile wiring.
- No change to review-loop convergence/cap semantics beyond making the Step 3.6 routing explicit.
