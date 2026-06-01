### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:54-58
- **Concern**: Orchestrator handoff omits exit-code contract for design-publish.sh. Scenario: Implementer may mirror design-route.sh (`if [[ _rc -ne 0 ]]; then abort`) or design-init-runparams exit-1 semantics; driver exit 1 is the normal plan-block-write failure path and must still parse `.design-publish-result.env` before branching
- **Proposed resolution**: Spell out in Step 5c: after `set +e` capture, exit 2 → configuration abort only; exit 1 → parse result env (do not abort); exit 0 → parse; any other rc → operational-failure abort (mirror Step 0b unexpected-rc pin)

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-publish.sh:28-29
- **Concern**: Plan-block-write failure branch not pinned under set -euo pipefail. Scenario: Item 4 calls plan-block-write.sh with no if ! or set +e; a non-zero exit aborts the driver before PLAN_WRITE_OK=false, failed-plan-write render, exit 1, and result-env write
- **Proposed resolution**: Pin if ! plan-block-write.sh ...; then success tail else failure tail (match design-init-runparams.sh if ! patterns)

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:446
- **Concern**: skills/design/SKILL.md:1321. Scenario: scripts/test-render-cost-line-callsites.sh:64-68
- **Proposed resolution**: Stale helper-exit-0 full-body emit gates Plan moves failed-plan-write render into design-publish.sh (exit 1) and requires orchestrator emit when FINAL_SUMMARY_PATH is non-empty regardless of PLAN_WRITE_OK, but Final summary block Step 5d and test-render-cost-line-callsites.sh still require helper exit 0 Orchestrator may skip verbatim final-summary.md on plan-block-write failure despite driver writing the file Update Final summary block and Step 5d prose to gate on non-empty final-summary.md (or parsed FINAL_SUMMARY_PATH) after design-publish.sh returns; relax or replace test-render-cost-line-callsites.sh:64-68 pins accordingly

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:348-363
- **Concern**: Plan relocates architecture-diagram pins to design-publish.sh but omits repointing the (15b) SKILL-window awk that orders plan-block-write.sh → upsert-diagrams-comment.sh → design-log-publish.sh. Scenario: After SKILL.md drops inline items 4–11, lines 348–352 still grep Step 5c prose for those scripts; test-design-structure.sh fails even if design-publish.sh pins are added
- **Proposed resolution**: In the test-design-structure.sh update, replace the step5c_line awk block (348–352) with equivalent line-order greps on skills/design/scripts/design-publish.sh (keep 337–340 validator-before-redact on SKILL)
