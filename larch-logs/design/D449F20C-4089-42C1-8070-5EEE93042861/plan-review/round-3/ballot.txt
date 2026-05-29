### FINDING_1: Case-local mocks must reset all assessment script overrides
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned integration case isolates `case_tmp` but does not reliably reset process-global `LARCH_*` mock overrides before the two-entry scenario, so earlier test mutations can make round 2 falsely pass or fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Install case-local mock-dispatch.sh and mock-monitor.sh under case_tmp; export all three LARCH_* paths to case_tmp (or re-seed $TMP stubs) immediately before Entry 1; set Entry 2 dispatch stub under case_tmp before the round-2 assess call.

### FINDING_2: MainAgent re-tally leaves stale Step 3 result state
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: After a successful MainAgent re-tally, Gate B may still read stale `.step3-plan-review-result.env` values from the earlier 0-judge fallback, preventing the path from being treated as complete-equivalent or routed through Step 3.6 correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a minimal step after the MainAgent re-tally: parse the re-tally output; on TALLY_PLAN_REVIEW_STATUS=ok set LOOP_STATUS=complete and TALLY_PLAN_REVIEW_STATUS=ok in the in-memory Step 3 variables and/or rewrite .step3-plan-review-result.env before entering Gate B; on tally-error use the existing short-circuit.

### FINDING_3: Integration coverage skips the Gate B settle leg
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned test manually calls cursor advancement, write-after, and `assess-plan-round`, so it does not prove that a Gate B settled path such as passive-summary Continue actually routes through Step 3.6 before the second Step 3 entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add a minimal validation that a Gate B settled path, especially passive-summary Continue, routes to Step 3.6 write-after before the second Step 3 entry/round-2 assessor assertion; if a full prompt harness is impractical, add a focused structural assertion that pins that exact settled-path routing.
