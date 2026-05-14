## Goal
Add LARCH_EXECUTION_ISSUES_LOG env-var precedence to execution_issue_log() resolvers so test harnesses can isolate their failure-capture target from the production run's execution-issues.md

## Implementation Plan
## Implementation Plan

### Goal
Prevent test-harness reviewer failures from leaking into the parent /implement run's execution-issues.md by adding LARCH_EXECUTION_ISSUES_LOG env-var precedence to every execution_issue_log() resolver.

### Files to modify

**Fix 1 — execution_issue_log() resolvers (3 scripts):**
- `skills/review/scripts/dispatch-panel.sh` — add LARCH_EXECUTION_ISSUES_LOG first-priority check
- `skills/review/scripts/collect-findings.sh` — same (duplicate resolver)
- `scripts/dispatch-plan-voters.sh` — same (third resolver found via grep)

Pattern (identical in all three):
```bash
execution_issue_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s' "$LARCH_EXECUTION_ISSUES_LOG"
        return
    fi
    # existing chain unchanged
    if [[ -n "$SESSION_ENV_PATH" ]]; then ...
```

**Fix 2 — test harnesses (11 scripts):**
Each gets this block in the setup area (after TEST_TMPDIR/TMPDIR is set, before subjects are invoked):
```bash
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR/execution-issues.md"
```
(Use whichever tmpdir variable name each harness already uses for its test sandbox.)

Harnesses to fix:
- `scripts/test-launch-review.sh` (Codex suite + Cursor suite sub-shells; each needs own export)
- `scripts/test-ci-wait.sh`
- `scripts/test-launch-cursor-ci.sh`
- `scripts/test-launch-codex-ci.sh`
- `scripts/test-run-external-agent.sh`
- `scripts/test-collect-agent-results.sh`
- `scripts/test-wait-for-reviewers.sh`
- `scripts/test-dispatch-plan-voters.sh`
- `skills/implement/scripts/test-codex-implementer.sh`
- `skills/implement/scripts/test-cursor-implementer.sh`
- `skills/implement/scripts/test-gemini-implementer.sh`

**Fix 3 — sibling .md docs:**
- `scripts/append-tool-failure.md` — document LARCH_EXECUTION_ISSUES_LOG not read by this script (callers compute the path); note callers use it
- `scripts/append-execution-issue.md` — same note  
- `skills/review/scripts/dispatch-panel.md` — document new env-var precedence chain
- `skills/review/scripts/collect-findings.md` — same
- `scripts/dispatch-plan-voters.md` — same (new doc for third resolver)

### Precedence chain
`LARCH_EXECUTION_ISSUES_LOG` > `SESSION_ENV_PATH/execution-issues.md` > `IMPLEMENT_TMPDIR/execution-issues.md` > `REVIEW_TMPDIR|DESIGN_TMPDIR/execution-issues.md`

### Verification
- Run /relevant-checks after implementation.
- grep for LARCH_EXECUTION_ISSUES_LOG to confirm all three resolvers and all test harnesses carry the pattern.

## Test plan
(no test plan section in plan-file)
