### [Plan Review] FINDING_3

### FINDING_3: Brainstorm external runtime failures shrink the panel instead of using fallback slots
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Cursor or Codex brainstorm runtime failures can reduce the intended panel size instead of following the existing per-slot fallback standard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: On non-OK collector status, log the failure and run a Claude replacement for that brainstorm slot, writing the same output path before synthesis; only proceed with fewer outputs if the replacement also fails


