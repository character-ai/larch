## Proposed Design Outline

### Goals
- Make Step 3.6 (plan-quality assessor) routing explicit and consistent on every Step 3 exit path.
- Skip Step 3.6 with a visible breadcrumb on `panel-failed` / `tally-error` / `cap-reached` short-circuits.
- Cover cursor-advance → Gate B settle → `write-after` → second Step 3 entry with an offline integration test.

### Non-goals
- No rework of `assess-plan-round.sh` / `snapshot-plan-round.sh` mechanics (round<2 skip, missing-snapshot, degraded-default-open stay).
- No new test harness file or Makefile target.
- No change to review-loop convergence/cap semantics beyond routing clarity.

### Approach sketch
- SKILL.md Step 3 branch matrix: add explicit "skip Step 3.6 (breadcrumb)" to the `tally-error` / `panel-failed` / `cap-reached` entries; confirm passive-summary (`converged|cap-hit`) already routes through 3.6.
- approval-gates.md: add `panel-failed` to the existing "skip Gate B (and therefore Step 3.6)" enumeration; keep `zero-findings-degraded-panel` routing THROUGH 3.6.
- Expand `test-assess-plan-round.sh` with a two-review-run integration case: cursor advance, `write-after`, assessor fires only on round ≥ 2.
- Reuse the existing `⏩ 3.6: assessor — …` breadcrumb grammar; introduce no new `LOOP_STATUS` tokens.

### Surfaces in scope
- `skills/design/SKILL.md` (Step 3 branch matrix; Step 3.5/3.6 prose)
- `skills/design/references/approval-gates.md` (Gate B / Gate C skip-3.6 enumeration)
- `skills/design/scripts/test-assess-plan-round.sh` (+ sibling `test-assess-plan-round.md`)

### Open questions
- None.
