### FINDING_10: [OUT_OF_SCOPE] Fresh fallback can reset persisted ship loop counters
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: When ship resume falls back to `start=="fresh"`, persisted CI loop counters can be written and then reset to zero at merge-loop entry, potentially bypassing loop caps after a transient mis-route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: When entering the merge loop after a fresh fallback, seed `iteration` / `rebase_count` / `fix_attempts` / `transient_retries` from `resume.*` (the same values already persisted in `ship-pr-state.sh`), or refuse fresh fallback when `PHASE=ci-initial` and counters indicate an in-progress merge loop unless an explicit operator reset flag is set.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] Corrupt ship resume counters silently reset to zero
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: important
- **Concern**: `read_resume_counters` maps non-numeric counter values to `0`, which can silently reset budgets from a damaged `ship-pr-state.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Treat non-numeric counter fields as a blocked resume (similar to invalid `BRANCH_NAME` / `PR_URL` handling in `_resume_plan`) or emit a loud parse warning and refuse `open-pr` resume until state is repaired.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] terminal ship failures now always persist PHASE=stalled
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `_write_terminal_state` always writes `PHASE=stalled` on failure, which may remove a `postmerge` signal used by gh-skipped merged detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: worth monitoring in forked/`repo_unavailable` runs.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


