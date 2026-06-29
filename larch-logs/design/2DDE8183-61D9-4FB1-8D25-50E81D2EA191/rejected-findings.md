### [Plan Review] FINDING_2

### FINDING_2: Relevant-check routing misses hook and marker source files
- **Reviewer(s)**: Cursor-Arch Phase2, Cursor-Pragmatic Phase2, Codex-Requirements
- **Severity**: important
- **Concern**: The run-relevant routing covers the new lint or harness files, but not all source files whose edits change marker, hook, or circuit-breaker behavior. Those edits can land without selecting the hook and structure harnesses that validate the behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch Phase2: Add direct-target rules for the edited shell sources so the hook and structure tests run when those files change, not just when the new lint or test files change.
  - From Cursor-Pragmatic Phase2: Add direct-target rules for `scripts/hook-bg-poll-guard.sh`, `scripts/hook-no-progress-guard.sh`, and their `scripts/test-hook-*.sh` harnesses so those tests are selected whenever the hook files change.
  - From Codex-Requirements: Add direct-target rules for those files to `checks_run_relevant.py` and route them to the hook harnesses; keep the new lint route for the bg-wait coverage files


