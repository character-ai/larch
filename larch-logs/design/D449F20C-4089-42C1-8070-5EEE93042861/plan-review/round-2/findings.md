### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1118
- **Concern**: Branch matrix remains silent for main-agent-vote-required. Scenario: The plan says every Step 3 exit will name its Step 3.6 disposition, but the existing main-agent-vote-required branch is not included in the proposed edits, leaving one LOOP_STATUS with ambiguous routing
- **Proposed resolution**: Add a minimal sentence to the main-agent-vote-required branch stating that after inline adjudication re-runs tally and produces normal artifacts, it proceeds to Gate B and then Step 3.6 on settled paths

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh:292
- **Concern**: The proposed round-2 integration assertion can pass on assessor fail-open instead of proving the assessor fired. Scenario: The plan tells the harness to point `LARCH_TALLY_PLAN_ASSESSOR_SH` at nonexistent `scripts/tally-plan-assessor.sh`, and `assess-plan-round.sh` degrades open by writing a `not-worse` verdict file; an assertion that only checks for a “real verdict” plus `assessor-verdict-round-2.txt` can pass without exercising the real tally path
- **Proposed resolution**: Point `LARCH_TALLY_PLAN_ASSESSOR_SH` to `$ROOT/skills/design/scripts/tally-plan-assessor.sh` and assert `ASSESSOR_STATUS=ok`, `ASSESSOR_VERDICT=worse-majority`, `EFFECTIVE_ASSESSORS=3`, and the round-2 verdict file exists

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh:17-20
- **Concern**: The new isolated integration case is specified to use a fresh sub-tmpdir but also says to call the existing write_params helper, which writes only to $TMP/run-params.json.. Scenario: assess-plan-round.sh run with --design-tmpdir pointing at the sub-tmpdir will not see run-params.json, will read workflow_path as unset, and will skip instead of exercising the HARD round-2 assessor path.
- **Proposed resolution**: Add a tiny parameterized helper for the new case, such as write_params_for "$case_tmp" HARD, or explicitly write "$case_tmp/run-params.json" before Entry 1; leave the existing write_params helper unchanged for current tests.

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-loop-status-completeness, Codex-dyn-loop-status-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:36-85; skills/design/scripts/plan-review-loop.sh:1243-1302; skills/design/SKILL.md:1117-1120
- **Concern**: Plan omits explicit Step 3.6 routing for emitted LOOP_STATUS=main-agent-vote-required. Scenario: plan-review-loop.sh emits main-agent-vote-required when zero eligible voters require inline adjudication, but the proposed prose additions cover tally-error, degraded-empty-collector, panel-failed, cap-reached, plan-size-trigger, and plan-validator-defects while leaving the existing inline path silent about whether successful MainAgent re-tally proceeds through Step 3.6; this violates the plan's stated every Step 3 exit rule and can leave Gate B relying on fallback behavior instead of an explicit route
- **Proposed resolution**: Add minimal prose to SKILL.md and approval-gates.md: after successful MainAgent re-tally, continue to Gate B as complete-equivalent, with zero-findings and settled Gate B paths proceeding through Step 3.6 before Step 3b; if the re-tally emits tally-error, use the tally-error short-circuit. Do not add main-agent-vote-required to skip lists.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-test-isolation-fidelity, Codex-dyn-test-isolation-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:145-150
- **Concern**: The plan says to reset plan-after-round-* / cursor / verdict artifacts between the two entries, but the proposed scenario depends on preserving plan-after-round-1.txt so the Step 3 cursor helper advances from 1 to 2. Current Step 3 only advances when plan-after-round-${ROUND_NUM}.txt exists, and Step 3.6 then runs write-after before assess-plan-round.sh.. Scenario: Following the reset-between-entries wording would delete the round-1 snapshot, keep the second entry at round 1, and skip the assessor instead of proving the round-2 fire path.
- **Proposed resolution**: Change the isolation wording to reset artifacts before this integration case and between independent cases, not between Entry 1 and Entry 2; preserve plan-after-round-1.txt through Entry 2 while still using a fresh case tempdir and fresh dispatch/monitor/tally pointers.
