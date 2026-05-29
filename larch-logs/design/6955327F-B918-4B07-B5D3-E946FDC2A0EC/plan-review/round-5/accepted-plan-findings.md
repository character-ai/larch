### FINDING_1: New harness target missing from `.PHONY`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: A new harness target (`test-gather-branch-context`) can be added to the Makefile recipe list and `test-harnesses-8` membership without a matching `.PHONY` entry. `scripts/test-harness-shards-coverage.sh` then fails `make lint` with “missing from .PHONY”.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add test-gather-branch-context to an existing .PHONY line (e.g. Makefile:4) in the same Makefile change


### FINDING_2: `dynamic-fail` / `dynamic-parse-failed*` fixtures not aligned with multi-tier terminal status
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan does not retarget `dynamic-fail` / `dynamic-parse-failed*` fixtures for multi-tier terminal status. With `--codex-available true`, dispatch forwards `--codex-present true`; a PATH `codex` stub that writes non-JSON to `${OUTPUT}.raw` (probe miss) then runs the Claude stub. `SCOUT_LAUNCH_FAIL` / malformed JSON no longer produce `SCOUT_STATUS=claude-failed` or `parse-failed` + diag—they produce `SCOUT_STATUS=empty` under the new exhaustion rule, which breaks grep expectations and parse-failed sidecar tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### UPDATED: skills/review/scripts/test-dispatch-panel.sh`, explicitly require: (1) `dynamic-parse-failed*` and prod warn cases use `--codex-available false` (single-tier `parse-failed` + diag), or update assertions to `empty` and drop parse-failed diag checks; (2) `dynamic-fail` use `--codex-available false` or a `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` stub that fails launch so the last-tier status stays `claude-failed`; document that ok/empty paths may rely on Codex non-JSON fallthrough but failure-path fixtures must be retargeted

