### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-dispatch-panel.sh:603-604
- **Concern**: Plan omits both-down Claude phase-3 count assertion update. Scenario: After 4-archetype both-down dispatch, harness still requires >=6 *phase3.txt files and fails despite correct 4-slot panel
- **Proposed resolution**: Add explicit plan step: change both-down case to expect >=4 phase-3 outputs (and sync breadcrumb greps from 6 to 4 where both-down)

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-specialist-prompt.sh:286-297
- **Concern**: Plan widens plan injection for reviewer-testing by DIFF_MODE only, but plan blocks still require MODE=diff. Scenario: After the fold, /review description mode still calls render-specialist-prompt with MODE=description and --plan-file; the existing guard is MODE==diff && DIFF_MODE==generic, so reviewer-testing never receives <implementation_plan> and the folded plan-fidelity secondary scan is blind in description reviews
- **Proposed resolution**: In reviewer-testing plan injection, also allow MODE=description when PLAN_FILE is readable; extend scripts/test-render-specialist-prompt.sh with a description-mode case

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-specialist-prompt.sh:284-297; scripts/test-render-specialist-prompt.sh:371-375
- **Concern**: Plan-fidelity fold injects plan for reviewer-testing only across DIFF_MODE variants; description mode still omits plan and tests assert that omission. Scenario: Step 5 can use description mode with --plan-file required; reviewer-testing loses folded plan-fidelity context and secondary scan is blind to the plan
- **Proposed resolution**: Add a reviewer-testing branch that injects implementation_plan whenever PLAN_FILE is readable in both diff and description modes; extend test-render-specialist-prompt.sh with description-mode coverage and relax the global description-mode no-plan assertion for reviewer-testing only

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-specialist-prompt.sh:284-297; scripts/test-render-specialist-prompt.sh:371-375
- **Concern**: Folded plan-fidelity is scoped to reviewer-testing across DIFF_MODE only; description mode still never injects PLAN_FILE and harness asserts that omission. Scenario: /description description-mode runs still require --plan-file (dispatch-panel.sh:99-101) but reviewer-testing gets no implementation_plan, so the folded secondary scan cannot run; existing test forbids description-mode plan injection globally
- **Proposed resolution**: Add reviewer-testing plan injection whenever PLAN_FILE is readable in both diff and description modes; extend test-render-specialist-prompt.sh with description-mode reviewer-testing coverage and narrow the no-plan assertion to non-testing agents only

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:92-97
- **Concern**: Plan mirrors /design both-vendor rows via output paths only; it never requires vendor-distinct manifest `.slot` values. Scenario: `queue_external_slot` still sets `"slot":"%s"` to the bare archetype slug. Emitting Cursor and Codex static rows (and Cursor/Codex dynamic twins) with the same slug duplicates slot IDs in `panel-manifest.ndjson`, unlike `dispatch-plan-review-panel.sh` (`cursor-plan-*` / `codex-plan-*`, `dyn-cursor-plan-*` / `dyn-codex-plan-*`). That collides drop diagnostics (`DROPPED_SLOTS_FILE` TSV), `dispatch-with-waterfall.sh` timing kinds (`${tool}-phase1-${slot}`), and dynamic tally attribution when `.slot` is used.
- **Proposed resolution**: Add explicit manifest contract to the plan: static slots `cursor-specialist-<archetype>` / `codex-specialist-<archetype>` (matching output basenames); dynamic slots `dyn-<name>` / `dyn-codex-<name>` with outputs `dyn-<name>-output.txt` / `dyn-<name>-codex-output.txt`. Refactor emission accordingly and assert unique `.slot` values in `test-dispatch-panel.sh`.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-threshold-denominator
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/dispatch-panel.sh:24-35; skills/review/scripts/check-reviewer-failure-threshold.sh:42-45
- **Concern**: Codex dynamic twin basename carve-out can bypass is_dynamic_reviewer_basename. Scenario: Plan permits non-dyn-* Codex dynamic output basenames while collector static/dynamic split keys off ^dyn-.*-output; design-style codex-primary-plan-dyn-* paths would be counted as static failures and can false-trigger >50% panel-failed despite partial static success
- **Proposed resolution**: Require dyn-${name}-codex-output.txt (remove or equivalent distinct basename) or extend is_dynamic_reviewer_basename to cover every permitted dynamic Codex basename before counting static FAILED_SLOTS
