### FINDING_4: Hook `kv get` failure can bypass active-bgjob denial
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: Missing fail-closed `kv get` failure coverage. After the planned replacement, a broken or unavailable Python CLI can yield no `CLONE_PATH`; treating that as no matching registry permits a background Bash despite an active same-clone daemon. A missing Python or failed `kv get` can bypass the active-bgjob denial when registry entries exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the hook harness to the plan and assert that a failing `kv get` with a valid matching registry still exits 0 and emits a denial.
  - From Codex-Requirements: Add fail-closed handling for CLI resolution or read failure when registry entries exist, and extend `scripts/test-hook-deny-run-in-background.sh` with a missing-Python or failing-`kv get` case that asserts exit-0 denial.


