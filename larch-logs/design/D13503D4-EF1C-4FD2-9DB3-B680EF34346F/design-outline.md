## Proposed Design Outline

### Goals
- Fold the Step 3 plan-candidate preview into `run-step3-review.sh` (first action), removing the separate orchestrator preview turn — saved on every Step 3 entry (2–5× on contested/HARD runs).
- Collapse the ~37-line Step 3 result-env consumption fence to the Phase 1 thin-fence shape: `out=$(driver); rc=$?; echo display; case "$rc"`.

### Non-goals
- No behavior change to the review panel, cap guard, round-cursor, branch matrix, or SIMPLE/HARD semantics.
- Do not touch any other `/design` fence — Round II Phases 3–7 are separate issues.

### Approach sketch
- `run-step3-review.sh`: after `larch_quiet_init` + plugin-root resolve, as the first action, render the step3 preview to the captured FD-3 display stream (survives the quiet-log redirect); the driver owns the `.step3-entry-plan-printed` first-entry sentinel.
- `emit-design-plan-preview.sh`: keep `gatec` for Step 4b; make the `step3` render reusable from the driver (renderer + FD routing), moving sentinel ownership to the driver.
- `SKILL.md` Step 3: delete the separate preview fence and the inline file-first/stdout/symlink parse loop; keep `.step3-review-result.env` as the machine-state source; echo captured display; branch on `LOOP_STATUS`/rc unchanged.
- Mirror the thinned fence in the two structure harnesses; keep `make lint` + affected harnesses green.

### Surfaces in scope
- `skills/design/scripts/run-step3-review.{sh,md}`
- `skills/design/scripts/emit-design-plan-preview.{sh,md}`
- `skills/design/SKILL.md` (Step 3 fence region)
- `skills/design/scripts/test-step3-orchestrator-fence.sh`, `scripts/test-design-structure.sh`
- Incidental harness sync: `test-emit-design-plan-preview.sh`, `test-run-step3-review.sh`

### Open questions
- None. Phase 1 is merged, so the thin-fence contract is fixed; FD-3 routing and sentinel ownership are plan-level mechanics.
