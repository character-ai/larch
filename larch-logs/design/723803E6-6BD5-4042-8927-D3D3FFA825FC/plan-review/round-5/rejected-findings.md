### [Plan Review] FINDING_3

### FINDING_3: Scrub-only failures can omit SCRUB_OK and allow full flush
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Some scrub-only preflight/staging failure paths may return without `SCRUB_OK=false`; if the caller only blocks on explicit false/nonzero, the full publish flush can still run after a failed scrub path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: In --scrub-only mode, make every expected failure path before or during staging/scrub emit SCRUB_OK=false, make design-publish require SCRUB_OK=true exactly before full flush, and add a missing-SCRUB_OK scrub-only test.


### [Plan Review] FINDING_4

### FINDING_4: Structure test checks marker after first publish call instead of full flush
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Test check (25) still orders the marker after the first `design-log-publish.sh` match, which could be the scrub-only call, allowing the full flush to occur after the reentry marker without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Change check (25) to use publish_flush_line (last non --scrub-only call) for marker ordering; keep rename < flush < marker


### [Plan Review] FINDING_6

### FINDING_6: Plan scope expands beyond the requested simple rename reorder
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan expands a simple rename reorder into scrub-only plumbing, new admission propagation, render-summary behavior, security docs, and implement-admission docs, adding behavior beyond the stated requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Restore the minimum plan: move only the rename in skills/design/scripts/design-publish.sh, keep existing full-publish scrub behavior, and limit docs/tests to design-publish.md, SKILL.md, test-design-publish.sh, and test-design-structure.sh updates needed for the reorder


### [Plan Review] FINDING_7

### FINDING_7: design-log-publish contract doc would be stale after scrub-only addition
- **Reviewer(s)**: Codex-dyn-cross-doc-drift
- **Severity**: important
- **Concern**: The sibling contract doc would still describe only full-publish `PUBLISH_OK` output and the old test invocation, omitting new scrub-only outputs and side-effect boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cross-doc-drift: Add scripts/design-log-publish.md as an UPDATED scope entry and document --scrub-only output, side-effect boundary, and harness invocation


