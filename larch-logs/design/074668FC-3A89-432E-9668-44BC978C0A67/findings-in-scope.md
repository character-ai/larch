### FINDING_1: Idempotent sentinel path must materialize accepted-OOS evidence before disposition checkpoint
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The early `prior_sentinel and not blocks` branch in `python/oos_filer.py` writes `oos-issues.ndjson` with filed URLs and stamps success without ensuring accepted-input files exist. After adding a disposition checkpoint, `disposition_gate` rejects ndjson-with-URLs when no accepted input paths exist (`python/file_oos.py:468-475`), so `test_idempotency_sentinel_skips_create_loop` and live retries fail with `disposition_checkpoint_failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Call the same accepted-evidence materialization helper on this branch whenever `_accepted_input_paths` are absent, before checkpoint and before `steps_ran.step9a1=true`; update that test to expect materialization plus checkpoint ordering

### FINDING_2: `_step9a1_heuristic` can overwrite explicit `steps_ran.step9a1=true`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_step9a1_heuristic` in `python/run_logs.py:1415-1441` omits an early return when manifest `steps_ran.step9a1` is explicitly `true`, and still treats zero-count `run-statistics.md` as incomplete. After `oos file` succeeds on an empty batch or stamps `step9a1=true`, `flush_logs_pre` can overwrite manifest `step9a1` to `false` because the heuristic returns `False` for run-statistics containing `0 OOS issue(s) filed` and never reads explicit `true` from `manifest.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Before ndjson/stats inference, return True when manifest `steps_ran.step9a1` is explicitly true; treat any post-checkpoint `run-statistics.md` as completion (or drop the zero-count regex for runs that passed disposition-checkpoint)

### FINDING_3: Shipped `/implement` SKILL.md Step 9a.1 completion semantics conflict with Python-path checkpoint behavior
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The plan changes Python Step 9a.1 completion semantics but omits updates to the shipped `/implement` prompt contract. Current SKILL.md text (NEVER #14–15 at `skills/implement/SKILL.md:58-60`, pre-ship `oos file` hook at `768-774`, bail-time invariant at `792`) still treats pre-gate `oos-issues.ndjson` as proof Step 9a.1 ran or as evidence that suppresses `steps_ran.step9a1=false`, and describes disposition-checkpoint primarily on the bash `OOS_PENDING` path. After a checkpoint-failed Python OOS filing leaves provisional `oos-issues.ndjson` without `run-statistics.md`, orchestrator and audit tooling can disagree on whether Step 9a.1 completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `skills/implement/SKILL.md` update: Step 9a.1 complete only with `run-statistics.md` or explicit `steps_ran.step9a1=true`; provisional ndjson alone is not completion
  - From Codex-Generic: Add `skills/implement/SKILL.md` to the plan and update the Python `oos file` and bail-time invariant text so only post-checkpoint `run-statistics.md` or explicit `steps_ran.step9a1=true` marks Step 9a.1 complete

### FINDING_4: OOS retry dedup keyed on title can miss after combine rewrites titles
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Retry matching in `python/oos_filer.py` (`_working_batch`, lines 104-124) keys dedup on normalized title. If checkpoint fails after partial issue creation and a combine step rewrites titles, a retry with the same accepted blocks and persisted ndjson may fail to match prior filings and re-file duplicate public issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Match persisted sentinel and ndjson by Filed URL first; secondary-match titles via existing `_normalize_title`; reuse `_FILED_URL_LINE_RE` and `_working_batch` patterns

### FINDING_5: Upgrade-larch dev-config cleanup not pinned to version root only
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan extends `TEST_FILE_CLEANUP_PATTERNS` in `python/upgrade_larch.py:27-42` but does not pin a root-only cleanup mechanism for six dev config files (`.pre-commit-config.yaml`, `.markdownlint.json`, etc.). Adding bare filename patterns to `TEST_FILE_CLEANUP_PATTERNS` globs any matching path under the cache tree via `version_root.glob(pattern)`, not only the version root directory (unlike `DEV_TOP_LEVEL_CLEANUP_DIRS` which uses `version_root / name` joins).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `DEV_ONLY_ROOT_CONFIG_FILES` tuple and delete with `version_root / name` joins like `DEV_TOP_LEVEL_CLEANUP_DIRS`

### FINDING_6: Plan omits `test_pr_body.py` coverage for bail-time `step9a1` stamping
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan names only `python/test_ship.py` or an unspecified final-report test for Step 9a.1 false stamping, but `_stamp_skipped_steps_for_terminal_report` lives in `python/pr_body.py:854-868` and neither `python/test_pr_body.py` nor `python/test_ship.py` covers `step9a1` stamping today. The ndjson-only fix in `pr_body.py` can ship without regression coverage because the plan does not pin `python/test_pr_body.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: python/test_pr_body.py` with an explicit test of `_stamp_skipped_steps_for_terminal_report` asserting ndjson without `run-statistics.md` still stamps `steps_ran.step9a1=false`
