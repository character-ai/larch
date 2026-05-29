### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh:67-102
- **Concern**: Integration case isolates case_tmp but not LARCH_* mock overrides. Scenario: The new two-entry case runs after earlier cases mutate process-global LARCH_DISPATCH_PLAN_ASSESSORS_SH, LARCH_BREADCRUMB_MONITOR_SH, and LARCH_TALLY_PLAN_ASSESSOR_SH (e.g. path-escape dispatch at 233-259, partial dispatch at 156-170, mock tally at 184-190). Plan only mandates restoring the real tally script; vague restore default stubs is easy to under-implement. Entry 2 can assert worse-majority while assess-plan-round.sh degrades open (false pass) or miss worse-majority (false fail).
- **Proposed resolution**: Install case-local mock-dispatch.sh and mock-monitor.sh under case_tmp; export all three LARCH_* paths to case_tmp (or re-seed $TMP stubs) immediately before Entry 1; set Entry 2 dispatch stub under case_tmp before the round-2 assess call.

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1120; skills/design/references/approval-gates.md:90-99
- **Concern**: MainAgent re-tally plan omits state refresh for the stale Step 3 result env. Scenario: After a 0-judge fallback, plan-review-loop has already written .step3-plan-review-result.env with LOOP_STATUS=main-agent-vote-required. A successful MainAgent tally emits ok and rewrites findings artifacts, but Gate B still reads the stale env and may not treat the path as complete-equivalent or route through Step 3.6 correctly.
- **Proposed resolution**: Add a minimal step after the MainAgent re-tally: parse the re-tally output; on TALLY_PLAN_REVIEW_STATUS=ok set LOOP_STATUS=complete and TALLY_PLAN_REVIEW_STATUS=ok in the in-memory Step 3 variables and/or rewrite .step3-plan-review-result.env before entering Gate B; on tally-error use the existing short-circuit.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh (planned in plan.txt:67-107)
- **Concern**: Planned integration case omits the required Gate B settle leg. Scenario: The feature description asks for an integration test covering Step 3 cursor advancement, Gate B settle, Step 3.6 write-after, and a second Step 3 entry. The proposed case manually calls cursor/write-after/assess-plan-round, so passive-summary Continue or another Gate B settled path could still skip Step 3.6 without the new harness catching it.
- **Proposed resolution**: Add a minimal validation that a Gate B settled path, especially passive-summary Continue, routes to Step 3.6 write-after before the second Step 3 entry/round-2 assessor assertion; if a full prompt harness is impractical, add a focused structural assertion that pins that exact settled-path routing.
