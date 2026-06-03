### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:762-771
- **Concern**: Step 2b lead-in prose still mandates bare ACTION=EMIT_PLAN after fences consolidate. Scenario: Orchestrator may run design-postplan-emit.sh and also follow the paragraph by piping ACTION=EMIT_PLAN again (double emit / divergent snapshot+validator paths)
- **Proposed resolution**: Rewrite the Immediately after saving plan.txt paragraph to name design-postplan-emit.sh --snapshot-original only; add a FINDING_4 grep pin that fails if ACTION=EMIT_PLAN remains in the Step 2b block outside the shared validator-failure section
