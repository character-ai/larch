### [Plan Review] FINDING_1

### FINDING_1: mkitmp ndjson seed conflates precondition vs disposition-gap paths
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `mkitmp` always seeds a RUN_ID-keyed `oos-issues.ndjson`, but the precondition case requires no resolvable ndjson. If the harness implements one shared `mkitmp`, the precondition test (exit 2) still finds the seeded ndjson and never reaches the pre-gate path, conflating disposition-gap and precondition scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add mkitmp option (or a second helper) to omit or hide ndjson for the precondition case; keep default mkitmp with ndjson for exit-1 disposition-gap (non-sec OOS requires resolvable ndjson per plan.txt:48)


