## Decision 1: Enumeration scope
- **Question**: Should the sweep cover only Steps 5-6, or the full SKILL.md?
- **Resolution**: Full SKILL.md sweep, prioritizing the Step 5–6 region but including easy wins in Steps 3, 7a, 8+. Excludes steps already folded by #5271 (commit-route) and #5274 (checks-failure + durable-bail macros).
- **Source**: user

## Decision 2: "Mechanical" definition
- **Question**: What counts as a mechanical parse-to-route chain?
- **Resolution**: A chain is mechanical when: (a) a background fence returns, (b) the orchestrator parses one or more KV keys, (c) on the happy path (pass/continue) it unconditionally launches the next background fence with no main-agent judgment. Only the happy path needs to be mechanical — repair paths (checks failure, stall) still surface to prose because they require main-agent action. Keep-safe: MAV ballot reading/voting, coder-main-agent repair, conflict resolution edits, rejected-findings tracking, architectural guidelines semantic assessment.
- **Source**: codebase

## Decision 3: Primary fold-candidate pairs
- **Question**: Which specific consecutive-background-fence pairs are in scope?
- **Resolution**: Three confirmed mechanical pairs (from SKILL.md inspection):
  1. Step 5 self-review: `run-step-checks.sh --site step5-self-review` → `commit-route --site step5-self-review` (on RELEVANT_CHECKS_OK=true)
  2. Step 5 MAV/coder aftermath: `run-step-checks.sh --site step5-review-fixes` → `step-5-resume.sh --ready-to-commit` (on RELEVANT_CHECKS_OK=true)
  3. Step 6→7: `run-step-checks.sh --site step6` → `commit-route --site step7` (on FILES_CHANGED=true, RELEVANT_CHECKS_OK=true)
  Step 3 is also a candidate: `run-step-checks.sh --site step3` always precedes Step 4 commit. Bootstrap and step-7a are already clean enough (single-background fences with simple KV routing).
- **Source**: codebase

## Decision 4: Implementation pattern
- **Question**: How should verbs be structured?
- **Resolution**: Follow the #5271 commit-route pattern. Each new verb is a Python cli verb that internally runs both fences as blocking subprocesses and emits a single NEXT_ACTION routing token. The verb runs as a single `run_in_background: true` Bash fence from the orchestrator's perspective. On checks failure the verb emits NEXT_ACTION=checks-failed (with failure log path) so the Checks Failure Entry Macro can still route prompt-side. Reduces 2 background turns to 1 on the common happy path.
- **Source**: codebase
