### [Plan Review] FINDING_2

### FINDING_2: Terminal-lib deletion plan ignores live orchestration consumers
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The terminal-lib cut list names only `hooks/pre-commit/sleep-seconds` (or similar narrow surface), but live orchestration shells still source `lib-quiet`, `lib-phantom-probe`, `lib-execution-issues`, and related terminal libs. At E3 time, scripts such as `skills/implement/scripts/step-2-post-dispatch.sh`, `flush-execution-issues.sh`, `generate-code-flow-diagram.sh`, `skills/design/scripts/design-step3-review.sh`, and others still source those libs. Hook-only refactors followed by lib deletion would break `/implement` Step 2 and related paths before G-track ports retire those consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend preflight/testing with an explicit enumerated runtime source scan (or add firm ### UPDATED entries for every remaining non-residual .sh) and treat any hit as block-E3 until cut; do not delete terminal libs on hook-only work


