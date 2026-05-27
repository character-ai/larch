### [Plan Review] FINDING_5

### FINDING_5: Outline asks for implementation approach before divergent sketches
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The pre-sketch outline gate can ask the main orchestrator to propose or secure approval for an implementation direction before the external sketch panel, undermining Step 2a’s anti-anchoring purpose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Replace Approach sketch with Alternatives to explore or Evaluation criteria before Step 2a, and defer concrete approach selection until sketches and dialectic have run


### [Plan Review] FINDING_10

### FINDING_10: Non-publication of outline artifact lacks validation
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The plan requires design-outline.md and outline headers to stay out of published artifacts, but the testing strategy does not verify composed-plan.md or the GitHub larch:plan block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a manual smoke assertion or structural test that Step 5c composition does not read design-outline.md and the produced composed-plan.md/larch:plan body contains no outline header


### [Plan Review] FINDING_12

### FINDING_12: Outline cancel hygiene lacks the final-summary invocation contract
- **Reviewer(s)**: Cursor-dyn-cancel-invocation-contract, Codex-dyn-cancel-invocation-contract
- **Severity**: important
- **Concern**: The proposed design-outline.md cancel path mentions cancellation summary handling but does not spell out the existing render-final-summary.sh contract, so implementers may omit required flags or environment and produce broken or incomplete summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cancel-invocation-contract: Expand §9 to: export SUMMARY_OUTCOME=cancelled-outline; run SKILL.md ### Final summary block fence (skills/design/SKILL.md:270-285) not a bare helper call—sources current-design-env, passes --outcome from SUMMARY_OUTCOME, --mode from jq .design_classification on run-params.json, DESIGN_TMPDIR/ISSUE_NUMBER/SESSION_ID, optional --repo, --post-publish-only
  - From Codex-dyn-cancel-invocation-contract: Revise the proposed cancel hygiene to require executing the exact SKILL.md Final summary block or explicitly list: SUMMARY_OUTCOME=cancelled-outline, --outcome, --mode derived from $DESIGN_TMPDIR/run-params.json with N/A fallback, DESIGN_TMPDIR, SESSION_ID, ISSUE_NUMBER, optional --repo, and --post-publish-only.


