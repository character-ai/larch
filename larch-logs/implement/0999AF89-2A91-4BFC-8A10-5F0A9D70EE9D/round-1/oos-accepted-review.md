### OOS_1: [OUT_OF_SCOPE] remove_python_larch_logs uses unguarded rmtree outside run-dir containment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-symlink-containment-output.txt
- **Severity**: latent
- **Concern**: `remove_python_larch_logs()` uses unguarded `rglob`/`rmtree` on `python/larch-logs/` without the `_within_run_dir`/`_contained` pattern. A symlink inside that tree could lure `rmtree` outside the intended directory. Pre-existing; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Apply the same _within_run_dir/_contained pattern or os.walk(follow_symlinks=False) if hardening action 9 is desired later.
  - From cursor-specialist-edge-cases-output.txt: Walk with followlinks=False and skip or reject paths resolving outside the target root before rmtree (same pattern as run-dir guards)


### OOS_2: [OUT_OF_SCOPE] _delete() unlinks sidecar paths without _within_run_dir guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `_delete()` unlinks sidecar paths without `_within_run_dir` even though primary paths are filtered. A contained `aggregator-output.txt` with `aggregator-output.txt.meta` symlinked outside the run dir could still delete the external sidecar target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Check _within_run_dir on every target in _delete() before unlink


