### [Plan Review] FINDING_4

### FINDING_4: Check 20 still pins removed Step 0b sub-step numbers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: Check 20 in `scripts/test-design-structure.sh` still greps removed Step 0b sub-step numbers (2.5, 2.5-bis, 5.5-bis). After SKILL.md drops those anchors, greps for 2.5 title-eligibility and fetch_line/filter_line/clarify_line ordering will fail unless replaced. The plan says to adjust ordering checks but does not name replacement literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: make lint fails on first structure run after SKILL rewrite When re-pointing Check 20/21, replace fetch→2.5→3 line-order asserts with stable anchors (e.g. design-route.sh invocation before clarify loop, cancel-title-filter ROUTE handling before clarify) and drop 2.5-bis/5.5-bis SKILL greps in favor of design-route.sh / design-init-runparams.sh pins already listed elsewhere in the plan.

