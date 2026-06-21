# Review Round 3

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_10: `_diagram_failure_capture` leaves prefixed Mermaid on stderr lines
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `_diagram_failure_capture` only strips whole diagram sections or lines that start with Mermaid syntax, so a generator failure with prefixed stderr like `ERROR graph TD A-->B` leaves `graph TD A-->B` in `DIAGRAM_REASON`. Step 7a then writes that reason to stdout and `execution-issues.md`, violating the bounded, Mermaid-free durable failure surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Sanitize the collapsed tail with `design_diagram_log.sanitize_diagram_capture` or fail closed when `_MERMAID_REMAINS_RE` matches, and add a regression where prefixed Mermaid appears on a stderr diagnostic line.


### FINDING_11: Step 5b annotate failure does not mark `step-5b` complete
- **Reviewer(s)**: dyn-diagram-flow-output.txt
- **Severity**: important
- **Concern**: Step 5b annotate failures (`step5b_annotate_main` returns non-zero) do not call `_step5b_mark_complete()`, so `.completed/step-5b` stays absent. `skills/design/SKILL.md` tells the orchestrator to continue to Step 5b.5 on partial `/issue` failure (`ISSUES_FAILED>0`, lines 812–813) and on other non-zero annotate exits without a partial contract (line 813). Step 5b.5 entry then hard-fails at `design-step3b-entry.sh:196-198` because `step-5b` is missing, and Step 5c / `publish_main` also fail closed on the same sentinel. Prepare failure is handled (`step5b_prepare_main` calls `_step5b_mark_complete()` at line 4092); annotate failure is not, so a non-blocking annotate failure blocks diagram generation and publish despite the SKILL contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-diagram-flow-output.txt: On every SKILL non-blocking annotate failure path (at minimum `ISSUES_FAILED>0`, and any other branch that says “continue to Step 5b.5”), call `_step5b_mark_complete()` before returning, mirroring the prepare-failure-continue path; add a regression test that partial annotate failure can reach Step 5b.5 and Step 5c.


