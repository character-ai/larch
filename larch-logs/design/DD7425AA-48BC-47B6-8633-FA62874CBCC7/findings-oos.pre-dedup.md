### OOS_1: Self-review path still bypasses tiered architectural knowledge
- **Description**: Self-review path still bypasses tiered architectural knowledge. Scenario: The issue requires reviewers to treat documented `I-*` / `G-*` violations as in-scope, but `--self-review` and `STEP5_REVIEW_STATUS=self-review-required` follow `self-review.md` without reading invariants/guidelines blocks or the new reviewer carve-out. Runs using self-review can miss the same documented violations the external review path is meant to enforce.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/self-review.md:1-51
- **Phase**: design



