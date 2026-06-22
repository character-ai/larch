### [Plan Review] FINDING_1

### FINDING_1: `_publish_run_tree_to_repo` deletes backup before dest check, breaking crash recovery
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The plan hardens `_copy_tree_to_repo` and `publish_breadcrumbs_main` with `_replace_tree_with_backup` and interrupted-publish recovery, but keeps `_publish_run_tree_to_repo` unchanged (or only partially aligned). That path still runs `shutil.rmtree(backup)` whenever `.{run_id}.old` exists before checking `dest`. After a crash between `dest.replace(backup)` and `tmp_dest.replace(dest)`, `dest` is missing and `backup` holds the only committed tree; the next publish via `_publish_run_tree_to_repo` (e.g. `flush_logs_pre` in ship Step 7a / CI monitor) deletes that backup and publishes fresh, violating the plan’s failure mode that the next publish must recover from backup and the issue acceptance on crash safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wire _publish_run_tree_to_repo through the same _replace_tree_with_backup helper (or add the same dest-missing backup-restore preamble and never rmtree backup when dest is absent). Align backup naming with the helper so refresh and flush commit paths share one recovery contract. Add a test mirroring the interrupted-publish case for _publish_run_tree_to_repo.
  - From Cursor-Pragmatic: Wire `_publish_run_tree_to_repo` through `_replace_tree_with_backup` with the same refuse gates as `_copy_tree_to_repo` (drop the unconditional `rmtree(backup)` block). Add one focused test mirroring the interrupted-publish recovery case for this path.

