### FINDING_2: Plan omits `docs/linting.md` from startup-lock rename
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits `docs/linting.md` from the full startup-lock rename. After the helper and env-var rename, the linting docs may still describe the run-negotiation-round harness as covering Darwin serial-lock acquire/release, leaving stale user-facing documentation for the renamed startup-lock contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add docs/linting.md to the plan and update the row to say Darwin startup-lock acquire/release, matching the new helper and env terminology.


