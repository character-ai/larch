## Decision 1: commit-route dependency status
- **Question**: Has the commit-route dependency issue been merged?
- **Resolution**: Yes. Issue #5271 "[DONE] md-to-py-V: fold commit-route (COMMIT_OUTCOME to NEXT_ACTION) into the commit verb" is CLOSED. The clean base is established.
- **Source**: codebase

## Decision 2: scope of changes
- **Question**: What exactly is in scope?
- **Resolution**: Two dedup operations in `skills/implement/SKILL.md`: (1) hoist checks-failure entry boilerplate to a named mini-section referenced by the 5 sites; (2) define a "durable-bail to Step 18" macro (parallel to Rebase Checkpoint Macro) referenced by the remaining manual-seed sites. No Python changes, no new references files.
- **Source**: issue body

## Decision 3: KEEP-safe constraint
- **Question**: Must judgment be preserved?
- **Resolution**: Yes. No routing logic is removed. The macro and mini-section are prose-only dedups; each call site supplies only its variable tokens (--site, STALL_STEP, STALL_REASON).
- **Source**: issue body
