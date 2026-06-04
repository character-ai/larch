### [Plan Review] FINDING_9

### FINDING_9: Auto-repair attempt cap is not persisted
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: If auto-repair remains in scope, an in-memory or prose-only two-attempt cap can be exceeded across pause/resume or multi-turn loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add DESIGN_TMPDIR attempt counter file and read increment in handler


### [Plan Review] FINDING_11

### FINDING_11: Preserve-tmpdir structural needle may be deleted
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Concern**: The existing preserve/skip-cleanup structural test needle appears only in Step 5c validator prose that the fold may delete, causing CI structure tests to fail unless the contract is preserved or the pin is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-handoff-control: Add literal preserve/skip-cleanup phrase to exit-4 or shared-handler Cancel prose or update pin


### [Plan Review] FINDING_12

### FINDING_12: Step 5c accept/override skip-validate path is not explicit
- **Reviewer(s)**: Cursor-dyn-handoff-control
- **Severity**: important
- **Concern**: The handler prose may not concretely require an operator accept/override at Step 5c to re-publish with `design-publish.sh --skip-validate`, leaving the accept path unable to bypass known validator defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-handoff-control: Rewrite shared handler in SKILL.md with auto-repair + Accept re-invoke design-publish.sh --skip-validate


