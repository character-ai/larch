### [Plan Review] FINDING_1

### FINDING_1: Idempotent sentinel path must materialize accepted-OOS evidence before disposition checkpoint
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The early `prior_sentinel and not blocks` branch in `python/oos_filer.py` writes `oos-issues.ndjson` with filed URLs and stamps success without ensuring accepted-input files exist. After adding a disposition checkpoint, `disposition_gate` rejects ndjson-with-URLs when no accepted input paths exist (`python/file_oos.py:468-475`), so `test_idempotency_sentinel_skips_create_loop` and live retries fail with `disposition_checkpoint_failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Call the same accepted-evidence materialization helper on this branch whenever `_accepted_input_paths` are absent, before checkpoint and before `steps_ran.step9a1=true`; update that test to expect materialization plus checkpoint ordering


### [Plan Review] FINDING_2

### FINDING_2: `_step9a1_heuristic` can overwrite explicit `steps_ran.step9a1=true`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_step9a1_heuristic` in `python/run_logs.py:1415-1441` omits an early return when manifest `steps_ran.step9a1` is explicitly `true`, and still treats zero-count `run-statistics.md` as incomplete. After `oos file` succeeds on an empty batch or stamps `step9a1=true`, `flush_logs_pre` can overwrite manifest `step9a1` to `false` because the heuristic returns `False` for run-statistics containing `0 OOS issue(s) filed` and never reads explicit `true` from `manifest.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before ndjson/stats inference, return True when manifest `steps_ran.step9a1` is explicitly true; treat any post-checkpoint `run-statistics.md` as completion (or drop the zero-count regex for runs that passed disposition-checkpoint)


### [Plan Review] FINDING_5

### FINDING_5: Upgrade-larch dev-config cleanup not pinned to version root only
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan extends `TEST_FILE_CLEANUP_PATTERNS` in `python/upgrade_larch.py:27-42` but does not pin a root-only cleanup mechanism for six dev config files (`.pre-commit-config.yaml`, `.markdownlint.json`, etc.). Adding bare filename patterns to `TEST_FILE_CLEANUP_PATTERNS` globs any matching path under the cache tree via `version_root.glob(pattern)`, not only the version root directory (unlike `DEV_TOP_LEVEL_CLEANUP_DIRS` which uses `version_root / name` joins).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `DEV_ONLY_ROOT_CONFIG_FILES` tuple and delete with `version_root / name` joins like `DEV_TOP_LEVEL_CLEANUP_DIRS`


