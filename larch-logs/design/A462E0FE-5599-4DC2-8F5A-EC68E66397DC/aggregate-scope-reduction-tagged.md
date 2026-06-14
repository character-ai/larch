### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:458-464
- **Concern**: [SCOPE-REDUCTION] New guard must replace the existing elif that sets only LOOP_STATUS=panel-failed. Scenario: The reported silent exit happens because orchestrator reads STEP3_REVIEW_LOOP_STATUS but the current elif at 458-461 can set LOOP_STATUS=panel-failed while STEP3_REVIEW_LOOP_STATUS stays empty and line 463 skips printing it
- **Proposed resolution**: Implement the guard as a replacement for lines 458-461, not an extra layer; on unrecoverable empty state always set and printf both STEP3_REVIEW_LOOP_STATUS=panel-failed and LOOP_STATUS=panel-failed

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:611-614; skills/design/scripts/design-step35.sh:90-104
- **Concern**: [SCOPE-REDUCTION] zero-findings LOOP_STATUS recovery is mapped into loop-mode complete despite legacy routing contracts. Scenario: When only LOOP_STATUS=zero-findings-degraded-panel is present, the plan sets STEP3_REVIEW_LOOP_STATUS=complete. The current legacy contract routes that LOOP_STATUS through Gate B and the heuristic continuation path only when STEP3_REVIEW_LOOP_STATUS is unset, and design-step35.sh only marks step-3 for zero-findings in that unset branch. The proposed mapping can skip the legacy path and may leave completion sentinels unset in the planned regression case.
- **Proposed resolution**: Remove the zero-findings-degraded-panel to complete recovery, normalization carve-out, and test case from this PR. If that recovery is truly required, also update the downstream Step 3.5 and branch-matrix contracts and add a test that proves the completion and routing behavior.
