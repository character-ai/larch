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


