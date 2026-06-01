### FINDING_1: design-publish orchestrator exit-code contract
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Step 5c orchestrator handoff for `design-publish.sh` omits an explicit exit-code contract. An implementer may mirror `design-route.sh` / `design-init-runparams.sh` and abort on any non-zero rc, or treat exit 1 like a configuration/operational failure. Exit 1 is the normal plan-block-write failure path: the orchestrator must still parse `.design-publish-result.env` before branching (including `PLAN_WRITE_OK=false` handling), not abort before reading the result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Spell out in Step 5c: after `set +e` capture, exit 2 → configuration abort only; exit 1 → parse result env (do not abort); exit 0 → parse; any other rc → operational-failure abort (mirror Step 0b unexpected-rc pin)


### FINDING_2: plan-block-write failure not pinned under set -e
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Under `set -euo pipefail`, `design-publish.sh` item 4 calls `plan-block-write.sh` without `if !` or `set +e`. A non-zero exit aborts the driver before `PLAN_WRITE_OK=false`, the failed-plan-write render path, `exit 1`, and writing `.design-publish-result.env`—defeating the intended contract-failure semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin if ! plan-block-write.sh ...; then success tail else failure tail (match design-init-runparams.sh if ! patterns)


### FINDING_3: Stale helper-exit-0 gates for final-summary emit
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan moves failed-plan-write rendering into `design-publish.sh` (driver exit 1) and requires orchestrator verbatim emit when `FINAL_SUMMARY_PATH` is non-empty regardless of `PLAN_WRITE_OK`, but Final summary block prose (~line 446), Step 5d (~line 1321), and `scripts/test-render-cost-line-callsites.sh` (lines 64–68) still gate full-body emit on `render-final-summary.sh` exit 0. On plan-block-write failure the driver may write `final-summary.md` while the orchestrator skips verbatim emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Stale helper-exit-0 full-body emit gates Plan moves failed-plan-write render into design-publish.sh (exit 1) and requires orchestrator emit when FINAL_SUMMARY_PATH is non-empty regardless of PLAN_WRITE_OK, but Final summary block Step 5d and test-render-cost-line-callsites.sh still require helper exit 0 Orchestrator may skip verbatim final-summary.md on plan-block-write failure despite driver writing the file Update Final summary block and Step 5d prose to gate on non-empty final-summary.md (or parsed FINAL_SUMMARY_PATH) after design-publish.sh returns; relax or replace test-render-cost-line-callsites.sh:64-68 pins accordingly


### FINDING_4: test-design-structure Step 5c script-order pins stale
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan relocates architecture-diagram and publish sequencing pins into `design-publish.sh` and drops inline Step 5c items 4–11 from `SKILL.md`, but `scripts/test-design-structure.sh` lines 348–352 still awk-grep `SKILL.md` for `plan-block-write.sh` → `upsert-diagrams-comment.sh` → `design-log-publish.sh` order. The test fails even if `design-publish.sh` pins are correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In the test-design-structure.sh update, replace the step5c_line awk block (348–352) with equivalent line-order greps on skills/design/scripts/design-publish.sh (keep 337–340 validator-before-redact on SKILL)

