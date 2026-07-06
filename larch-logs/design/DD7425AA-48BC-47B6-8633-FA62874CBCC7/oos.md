### FINDING_3: Implementer validation misses `needs_qa` acknowledgment checks
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Implementer-side manifest checks need to enforce architectural acknowledgment for both complete and needs_qa when knowledge is required, not just validate `needs_qa.questions` structurally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add conditional jq (or an equally explicit pre-rename check) for both `complete` and `needs_qa` branches when the launcher included the architectural-knowledge section, and extend the required-fields table accordingly.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Self-review path still bypasses tiered architectural knowledge
- **Description**: Self-review path still bypasses tiered architectural knowledge. Scenario: The issue requires reviewers to treat documented `I-*` / `G-*` violations as in-scope, but `--self-review` and `STEP5_REVIEW_STATUS=self-review-required` follow `self-review.md` without reading invariants/guidelines blocks or the new reviewer carve-out. Runs using self-review can miss the same documented violations the external review path is meant to enforce.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/self-review.md:1-51
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

