### FINDING_1: Missing Step 3.6 route for main-agent-vote-required
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-loop-status-completeness, Codex-dyn-loop-status-completeness
- **Severity**: important
- **Concern**: The proposed routing matrix does not explicitly define how `LOOP_STATUS=main-agent-vote-required` proceeds after inline adjudication and re-tally. This leaves one Step 3 exit path ambiguous, despite the plan requiring every Step 3 exit to name its Step 3.6 disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a minimal sentence to the main-agent-vote-required branch stating that after inline adjudication re-runs tally and produces normal artifacts, it proceeds to Gate B and then Step 3.6 on settled paths
  - From Cursor-dyn-loop-status-completeness, Codex-dyn-loop-status-completeness: Add minimal prose to SKILL.md and approval-gates.md: after successful MainAgent re-tally, continue to Gate B as complete-equivalent, with zero-findings and settled Gate B paths proceeding through Step 3.6 before Step 3b; if the re-tally emits tally-error, use the tally-error short-circuit. Do not add main-agent-vote-required to skip lists.


### FINDING_2: Round-2 assessor test can pass via fail-open path
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Concern**: The proposed round-2 integration assertion may pass without exercising the real tally assessor because the configured assessor path is nonexistent and `assess-plan-round.sh` can degrade open by writing a `not-worse` verdict.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Point `LARCH_TALLY_PLAN_ASSESSOR_SH` to `$ROOT/skills/design/scripts/tally-plan-assessor.sh` and assert `ASSESSOR_STATUS=ok`, `ASSESSOR_VERDICT=worse-majority`, `EFFECTIVE_ASSESSORS=3`, and the round-2 verdict file exists


### FINDING_3: Isolated integration case writes params to wrong tempdir
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The new isolated integration case is meant to run in a fresh sub-tempdir, but reusing the existing `write_params` helper writes `run-params.json` only to `$TMP`, so `assess-plan-round.sh --design-tmpdir "$case_tmp"` will not see the expected params and may skip instead of exercising the HARD round-2 assessor path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a tiny parameterized helper for the new case, such as write_params_for "$case_tmp" HARD, or explicitly write "$case_tmp/run-params.json" before Entry 1; leave the existing write_params helper unchanged for current tests.


### FINDING_4: Integration case reset would delete required round-1 snapshot
- **Reviewer(s)**: Cursor-dyn-test-isolation-fidelity, Codex-dyn-test-isolation-fidelity
- **Severity**: important
- **Concern**: The plan says to reset `plan-after-round-*`, cursor, and verdict artifacts between the two entries, but Entry 2 depends on preserving `plan-after-round-1.txt` so the cursor helper advances to round 2 and triggers the assessor path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-isolation-fidelity, Codex-dyn-test-isolation-fidelity: Change the isolation wording to reset artifacts before this integration case and between independent cases, not between Entry 1 and Entry 2; preserve plan-after-round-1.txt through Entry 2 while still using a fresh case tempdir and fresh dispatch/monitor/tally pointers.

