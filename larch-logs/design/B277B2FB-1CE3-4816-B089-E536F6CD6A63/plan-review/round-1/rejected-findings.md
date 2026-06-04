### [Plan Review] FINDING_1

### FINDING_1: `--with-plan-size` must disable quiet mode for size-check KV capture
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `design-postplan-emit.sh --with-plan-size` may fail to parse `check-plan-size.sh` result KVs because `emit_kv` output is redirected to FD 3 under quiet mode, breaking hard-trigger/partition exit mapping and display behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Invoke check-plan-size with export LARCH_QUIET_DISABLE=1 (same capture contract as SKILL.md Step 2b.5:985-987) and parse stdout KVs into the result env before emit display lines


