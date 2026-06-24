### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:732-738
- **Concern**: [SCOPE-REDUCTION] Step 4 tail long-running contract is specified inside the wrapper but SKILL.md still runs `design-step3b-tail.sh` as a foreground Bash fence with no raised timeout or immediate-background wait.. Scenario: The plan requires up to 300-600s of parallel debater/judge work before Gate C preview (`dialectic-clarifier.md` long-running contract; `design-step3b-tail.sh` must not block on debate). `immediate-background` is an orchestrator Bash-tool flag; a foreground Step 4 fence will still hit the default Bash timeout or fail-open mid-debate on contested-fork runs, violating the issue's cost-discipline and no-new-halt constraints.
- **Proposed resolution**: Update `skills/design/SKILL.md` Step 4 explicitly: when fingerprint-valid candidates exist and `skip_approve_requested=false`, run `design-step3b-tail.sh` with `run_in_background: true` and `timeout` ≥ clarifier budget + slack (≥900s), wait on `<task-notification>` / `.completed/dialectic-gatec-terminal`, then continue to Step 4b; keep sync foreground only for no-candidate/no-debate paths. Add the sentinel to `skills/shared/design-background-wait.md` or document an equivalent probe in the Step 4 fence.
