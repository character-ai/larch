### FINDING_2: cleanup.md Edit-in-sync still references top-level mtime after invariant change
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan rewrites retention invariants for bounded nested-activity deletion but instructs keeping the Edit-in-sync bullet verbatim with "top-level mtime age checks." After landing, the contract doc would describe nested-activity / maxdepth-5 retention in Invariants while Edit-in-sync still tells maintainers to sync on top-level mtime checks, reintroducing the same doc drift this change is meant to fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: When updating Invariants, reword the Edit-in-sync trigger to nested-activity / maxdepth-5 retention (same file touch; no runtime change)

