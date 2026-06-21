# Review Round 2

- Mode: `diff`
- 3 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_4: Missing happy-path integration test for post-ensure pr-created snapshot
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-merge-log-path-output.txt
- **Severity**: important
- **Concern**: No integration test asserts the acceptance outcome for a straight green merge: `final-summary.md` heading `pr-created`, manifest `status: in-progress`, and `steps_ran.step8=true` after post-ensure flush. `test_straight_merge_post_ensure_committed_snapshot` exercises a post-monitor CI-failure path expecting terminal bail/stalled, not the happy path. Regression removing post-ensure `pr-created` flush could ship without failing targeted tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add green-CI straight-merge test asserting pr-created in-progress and step8=true
  - From cursor-specialist-testing-output.txt: Add or retarget an integration test with Outcome.OK monitor, assert final-summary pr-created, manifest status in-progress, and step8=true after post-ensure flush.
  - From dyn-merge-log-path-output.txt: Add a happy-path merge test with real `_REAL_FLUSH_LOGS_PRE`, mocked green `monitor` + `merge_pr`, and assertions on committed `pr-created` / `in-progress` artifacts.


### FINDING_8: Missing multi-flush sequence test (pre-PR bailed then post-PR pr-created)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required multi-flush sequence test is absent. Two-flush ordering bugs could leave committed artifacts on bailed while isolated cascade/flush unit tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test simulating pre-ensure_pr then post-ensure_pr state transitions through write_final_report/flush_logs_pre.


### FINDING_9: Stale finalize PHASE=stalled forces wrong post-ensure snapshot on resume
- **Reviewer(s)**: dyn-merge-log-path-output.txt
- **Severity**: important
- **Concern**: Post-ensure strict flush derives outcome from `normalized_outcome_values`, which treats `finalize-state.sh` `PHASE=stalled` as terminal even when `ship.py` has rewritten `ship-pr-state.sh` to `PHASE=ci-initial` for a resumed merge loop. Stall recovery clears `STALL_TRACKING`, `BAIL_REASON`, and `EXIT_CODE` but not `PHASE`, so a prior stall can leave `PHASE=stalled` and force post-ensure snapshots to `stalled`/`bailed` instead of `pr-created` on the common resume-after-stall path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-merge-log-path-output.txt: On healthy merge-loop re-entry (or in `_is_healthy_pre_terminal_pr_snapshot`), ignore stale finalize terminal keys when all stall layers are clear and ship phase is in-flight (`ci-initial`/`rebase`/`pr-create`); alternatively extend stall-clear to reset finalize `PHASE` (and related terminal overlay fields) before `run_ship` resumes.


