### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: No-touch sidecar behavior is unpinned
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The dispatch test no longer recreates the stale legacy sidecar fixtures, so it does not actually pin the no-touch behavior on existing sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: restore the stale sidecar setup and assert those files still exist after checks_commit_route_main so the no-touch behavior is pinned


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Residual Bash manifest omits the new harness
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The new extinct-notification harness is not in the residual Bash manifest, so Bash lint coverage will not scan it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: add scripts/test-extinct-notification-stack.sh to scripts/residual-bash-paths.txt so the new harness stays under Bash lint coverage


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

