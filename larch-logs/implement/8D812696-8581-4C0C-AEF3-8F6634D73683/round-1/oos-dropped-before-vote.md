### OOS_1: [OUT_OF_SCOPE] Missing blank line before Secondary scan heading
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The compressed necessity-gate paragraph runs directly into the `## Secondary scan` heading. That makes the Markdown section boundary slightly ambiguous and inconsistent with the other agents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Insert blank line before `## Secondary scan` in edge-cases and testing agents plus pre-rendered bodies.

### OOS_2: [OUT_OF_SCOPE] Panel-tier compression is still slightly short of target
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-reviewer-contracts
- **Severity**: nit
- **Concern**: The panel-tier compression lands at about 13% instead of the stated ~15% target, so the reduction is meaningful but still a little short of goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Optional second compression pass on non-contract prose if the issue owner requires >=15%.
  - From dyn-dyn-reviewer-contracts: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Run-log flush remains outside reviewer-contract scope
- **Reviewer(s)**: dyn-dyn-reviewer-contracts
- **Severity**: nit
- **Concern**: The run-log flush change is outside reviewer-contract scope, and the reviewer prompts already tell reviewers not to flag these commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-reviewer-contracts: Address the concern above.

