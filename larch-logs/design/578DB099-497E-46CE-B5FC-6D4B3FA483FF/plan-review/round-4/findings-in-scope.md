Validating reviewer findings against the codebase, then producing the normalized aggregator output.
Merged six raw inputs into four findings: FINDING_2–4 share one behavioral gap (description-mode plan injection for folded plan-fidelity in `reviewer-testing`); the rest stay separate.

### FINDING_1: Both-down harness still expects six phase-3 Claude outputs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The implementation plan does not update the both-down case in `test-dispatch-panel.sh`. After a 4-archetype both-down dispatch (four static Claude phase-3 slots instead of six), the harness still requires `>=6` `*phase3.txt` files and will fail even when dispatch is correct for the reduced panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit plan step: change both-down case to expect >=4 phase-3 outputs (and sync breadcrumb greps from 6 to 4 where both-down)

### FINDING_2: Folded plan-fidelity omits plan injection in description mode
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan widens plan injection for `reviewer-testing` by `DIFF_MODE` only, while plan blocks still require `MODE=diff`. Today `render-specialist-prompt.sh` injects `<implementation_plan>` only when `MODE == diff && DIFF_MODE == generic` (lines 284–297). `/review` description mode calls the renderer with `MODE=description` and `--plan-file` (required by `dispatch-panel.sh`), so `reviewer-testing` never receives the plan and the folded plan-fidelity secondary scan is blind in description reviews. `test-render-specialist-prompt.sh` (lines 371–375) asserts that description mode must not inject plan content globally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In reviewer-testing plan injection, also allow MODE=description when PLAN_FILE is readable; extend scripts/test-render-specialist-prompt.sh with a description-mode case
  - From Cursor-Innovation: Add a reviewer-testing branch that injects implementation_plan whenever PLAN_FILE is readable in both diff and description modes; extend test-render-specialist-prompt.sh with description-mode coverage and relax the global description-mode no-plan assertion for reviewer-testing only
  - From Cursor-Innovation: Add reviewer-testing plan injection whenever PLAN_FILE is readable in both diff and description modes; extend test-render-specialist-prompt.sh with description-mode reviewer-testing coverage and narrow the no-plan assertion to non-testing agents only

### FINDING_3: Manifest `.slot` values are not vendor-distinct
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan mirrors `/design` both-vendor rows via output paths only and does not require vendor-distinct manifest `.slot` values. `queue_external_slot` still sets `"slot":"%s"` to the bare archetype slug (e.g. `testing`). Emitting Cursor and Codex static rows (and Cursor/Codex dynamic twins) with the same slug duplicates slot IDs in `panel-manifest.ndjson`, unlike `dispatch-plan-review-panel.sh` (`cursor-plan-*` / `codex-plan-*`, `dyn-cursor-plan-*` / `dyn-codex-plan-*`). That collides drop diagnostics (`DROPPED_SLOTS_FILE` TSV), `dispatch-with-waterfall.sh` timing kinds (`${tool}-phase1-${slot}`), and dynamic tally attribution when `.slot` is used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit manifest contract to the plan: static slots `cursor-specialist-<archetype>` / `codex-specialist-<archetype>` (matching output basenames); dynamic slots `dyn-<name>` / `dyn-codex-<name>` with outputs `dyn-<name>-output.txt` / `dyn-<name>-codex-output.txt`. Refactor emission accordingly and assert unique `.slot` values in `test-dispatch-panel.sh`.

### FINDING_4: Codex dynamic basename may bypass failure-threshold dynamic carve-out
- **Reviewer(s)**: Cursor-dyn-threshold-denominator
- **Severity**: important
- **Concern**: The plan permits non-`dyn-*` Codex dynamic output basenames while `is_dynamic_reviewer_basename` in `check-reviewer-failure-threshold.sh` only matches `^dyn-.*-output`. Design-style `codex-primary-plan-dyn-*` paths would be counted as static failures and can false-trigger `>50%` panel-failed despite partial static success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-threshold-denominator: Require dyn-${name}-codex-output.txt (remove or equivalent distinct basename) or extend is_dynamic_reviewer_basename to cover every permitted dynamic Codex basename before counting static FAILED_SLOTS
