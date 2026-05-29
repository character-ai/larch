### [Plan Review] FINDING_3

### FINDING_3: Cleanup scan depth can delete active design sessions
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `find -maxdepth 5` does not see fresh `/design` plan-review leaves below the implement round-file boundary, so active design session roots with stale ancestor mtimes can be misclassified as stale and deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Raise the scan to `-maxdepth 6` (covers design round files and the `revise/` directory), add a `test-cleanup.sh` case for a stale session root with a fresh `plan-review/round-1/revise/codex-output.txt` (or equivalent depth-6/7 fixture), and update `cleanup.md` / SKILL edge-case text so the documented boundary matches implement **and** design layouts


### [Plan Review] FINDING_4

### FINDING_4: Cleanup retention env var conflicts with fixed-window policy
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: Adding `LARCH_CLEANUP_RETENTION_DAYS` creates a new public configuration surface, validation, docs, and tests even though the resolved policy is a fixed seven-day cleanup window for a SIMPLE-tier change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Hardcode the 7-day retention as a local constant in cleanup.sh; drop LARCH_CLEANUP_RETENTION_DAYS validation, docs entry, and invalid-retention harness case
  - From Cursor-Pragmatic, Codex-Pragmatic: Hard-code the 7-day retention in cleanup.sh and drop the env-var validation, configuration docs entry, and invalid-retention harness case


