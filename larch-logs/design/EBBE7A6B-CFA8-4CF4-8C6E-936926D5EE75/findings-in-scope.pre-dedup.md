### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/run_logs.py:1521-1525
- **Concern**: _publish_run_tree_to_repo still deletes backup when dest is missing. Scenario: The plan hardens _copy_tree_to_repo and publish_breadcrumbs_main with _replace_tree_with_backup and interrupted-publish recovery, but explicitly keeps _publish_run_tree_to_repo unchanged. That path still runs shutil.rmtree(backup) whenever backup exists before checking dest. After a crash between dest.replace(backup) and tmp_dest.replace(dest), dest is missing and backup holds the only committed tree; the next _larch_log_commit publish deletes that backup and publishes fresh, violating the plan failure mode that the next publish must recover via backup and the issue acceptance on crash safety.
- **Proposed resolution**: Wire _publish_run_tree_to_repo through the same _replace_tree_with_backup helper (or add the same dest-missing backup-restore preamble and never rmtree backup when dest is absent). Align backup naming with the helper so refresh and flush commit paths share one recovery contract. Add a test mirroring the interrupted-publish case for _publish_run_tree_to_repo.



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:1520-1527
- **Concern**: Plan defers `_publish_run_tree_to_repo` but its failure modes require interrupted-publish recovery. Scenario: `flush_logs_pre` (ship, Step 7a, CI monitor) publishes via `_publish_run_tree_to_repo`. On retry after a crash left only `.{run_id}.old` and `dest` missing, line 1521-1522 still `shutil.rmtree(backup)` before `tmp_dest.replace(dest)`, destroying the sole committed tree. Plan lines 132-133 require the next publish to recover from backup; line 53 keeps this path unchanged.
- **Proposed resolution**: Wire `_publish_run_tree_to_repo` through `_replace_tree_with_backup` with the same refuse gates as `_copy_tree_to_repo` (drop the unconditional `rmtree(backup)` block). Add one focused test mirroring the interrupted-publish recovery case for this path.



