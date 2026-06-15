### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/oos_filer.py:483-488
- **Concern**: Idempotent sentinel path must materialize accepted-OOS files before disposition checkpoint. Scenario: The early `prior_sentinel and not blocks` branch writes `oos-issues.ndjson` with filed URLs then stamps success today; after adding checkpoint, `disposition_gate` rejects ndjson-with-URLs when no accepted input files exist (`python/file_oos.py:468-475`), so `test_idempotency_sentinel_skips_create_loop` and live retries fail with `disposition_checkpoint_failed`
- **Proposed resolution**: Call the same accepted-evidence materialization helper on this branch whenever `_accepted_input_paths` are absent, before checkpoint and before `steps_ran.step9a1=true`; update that test to expect materialization plus checkpoint ordering

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/run_logs.py:1415-1441
- **Concern**: _step9a1_heuristic revision omits explicit steps_ran.step9a1=true and still treats zero-count run-statistics as incomplete. Scenario: After oos file succeeds on an empty batch or stamps step9a1=true, flush_logs_pre can overwrite manifest step9a1 to false because the heuristic returns False for run-statistics.md containing 0 OOS issue(s) filed and never reads explicit true from manifest.json
- **Proposed resolution**: Before ndjson/stats inference, return True when manifest steps_ran.step9a1 is explicitly true; treat any post-checkpoint run-statistics.md as completion (or drop the zero-count regex for runs that passed disposition-checkpoint)

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:792
- **Concern**: Bail-time Step 9a.1 invariant still treats pre-gate oos-issues.ndjson as proof the step did not run. Scenario: After checkpoint failure provisional ndjson exists without run-statistics; SKILL prose still says ndjson presence means before Step 9a.1, conflicting with new completion semantics
- **Proposed resolution**: Add skills/implement/SKILL.md update: Step 9a.1 complete only with run-statistics.md or explicit steps_ran.step9a1=true; provisional ndjson alone is not completion

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/oos_filer.py:504-536
- **Concern**: Retry matching keyed on title or vague stable identifier can miss after combine rewrites titles. Scenario: Checkpoint fails after issue create-one; retry with same accepted blocks and persisted ndjson may re-file duplicate public issues
- **Proposed resolution**: Match persisted sentinel and ndjson by Filed URL first; secondary-match titles via existing _normalize_title; reuse _FILED_URL_LINE_RE and _working_batch patterns

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/upgrade_larch.py:27-42
- **Concern**: Plan does not pin root-only cleanup mechanism for six dev config files. Scenario: Adding patterns to TEST_FILE_CLEANUP_PATTERNS globs any matching path under the cache tree, not just version root
- **Proposed resolution**: Add DEV_ONLY_ROOT_CONFIG_FILES tuple and delete with version_root / name joins like DEV_TOP_LEVEL_CLEANUP_DIRS

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/pr_body.py:867-868
- **Concern**: Plan names only python/test_ship.py or an unspecified final-report test for Step 9a.1 false stamping, but _stamp_skipped_steps_for_terminal_report lives in pr_body.py and neither test_pr_body.py nor test_ship.py covers step9a1 stamping today. Scenario: The ndjson-only fix in pr_body.py can ship without regression coverage because the plan does not pin python/test_pr_body.py
- **Proposed resolution**: Add ### UPDATED: python/test_pr_body.py with an explicit test of _stamp_skipped_steps_for_terminal_report asserting ndjson without run-statistics.md still stamps steps_ran.step9a1=false

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:58-60,768-792
- **Concern**: Plan changes Python Step 9a.1 completion semantics but omits the shipped /implement prompt contract. Scenario: After a checkpoint-failed Python OOS filing leaves provisional oos-issues.ndjson, the unchanged prompt text still says ndjson suppresses step9a1=false and describes checkpoint only on the bash path
- **Proposed resolution**: Add skills/implement/SKILL.md to the plan and update the Python oos file and bail-time invariant text so only post-checkpoint run-statistics.md or explicit steps_ran.step9a1=true marks Step 9a.1 complete

