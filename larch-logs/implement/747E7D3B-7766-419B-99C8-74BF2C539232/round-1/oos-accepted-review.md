### OOS_1: [OUT_OF_SCOPE] Thin postplan rc pytest coverage relative to plan
- **Reviewer(s)**: dyn-postplan-rc-output.txt
- **Severity**: important
- **Concern**: Postplan rc coverage is thin relative to the plan: only rc `10` (standalone postplan) and `step2b5` stdout/rc are tested. Missing direct tests for rc `11` pause `sys.exit`, rc `12`/`13` nonfatal exit `0` + row emission, fatal emit rc `1`/`2` → process exit `1`, drafter wrapper-row ordering (`DRAFTER_STATUS=succeeded` only after nonfatal capture), and fatal emit rc `2` not surfacing as process exit `2`.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] No symlink rehydration test for Step 2 / validator launcher path
- **Reviewer(s)**: dyn-env-rehydrate-output.txt
- **Severity**: latent
- **Concern**: `python/test_design_lifecycle.py:1091-1106` covers symlink session-env loading for `step0c` via `_load_source_env`, but there is no equivalent test that `design step2a` / `step2b-drafter` / `plan validator-autofix` rehydrate `ISSUE_NUMBER` and `DESIGN_TMPDIR` through the launcher symlink path; the existing `test_wrapper_session_env_parser_exports_quoted_paths` uses a regular file, so it would not catch the symlink regression.
- **Suggested revisions (informational for voters; coder decides)**:


