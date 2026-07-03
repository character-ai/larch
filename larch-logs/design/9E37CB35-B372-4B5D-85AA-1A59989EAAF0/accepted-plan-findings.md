### FINDING_1: Step 0-pre still forces a pre-0a flags read
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Step 0-pre gating still requires reading `flags.md` before the new Python-driven validation path, so the eager-closure reduction can still be blocked on every `/design` run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the Step 0-pre section, change the When line to run immediately before Step 0a (or before session setup) with no flags.md read prerequisite. Align any nearby Step 0-pre prose that still implies flags.md is required first.


