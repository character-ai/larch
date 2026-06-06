### [Plan Review] FINDING_3

### FINDING_3: Planned auth linter stack may be unnecessary scope
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a broad new lint stack in the same PR that rewires all known `codex exec` sites, creating extra maintenance surface without addressing an immediate uncovered call-site gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Defer the lint stack to a follow-up (or drop it): land launcher routing + negotiation inline auth + harnesses for those paths only; add the static guard only if a later change reintroduces raw `codex exec`


