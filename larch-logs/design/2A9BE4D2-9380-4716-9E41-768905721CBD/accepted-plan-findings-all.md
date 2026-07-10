### FINDING_1: Missing-workflow classification must use raw gh results
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Workflow Gate Integrator
- **Severity**: major
- **Concern**: `read_main_health()` still needs to inspect the raw `CommandResult` from `gh.run_list_filtered_read()` before any `ShipError` conversion, because the current `run_list_filtered()` path drops stderr/stdout and makes the missing-workflow signature impossible to classify. Without that refactor, repos that lack the configured `CI` workflow will still surface `MAIN_CI_STATUS=error` instead of `skip`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In read_main_health, call gh.run_list_filtered_read(), run the missing-workflow helper on non-zero rc before any raise, return skip only when query.workflow equals config.MAIN_HEALTH_DEFAULT_WORKFLOW, then parse JSON on rc 0 (reuse run_list_filtered parsing or factor a shared parser)
  - From Cursor-Pragmatic: In read_main_health, call gh.run_list_filtered_read, run the new gh helper on non-zero rc using _combined(result), return MainHealthStatus(status=skip) only when query.workflow == config.MAIN_HEALTH_DEFAULT_WORKFLOW and the helper matches; otherwise keep existing error handling. Parse JSON only after rc==0 or non-skip classification
  - From Cursor-dyn-Workflow Gate Integrator: In main_health.py plan bullet, require run_list_filtered_read plus helper classification on non-zero before _raise_read_failure or the generic ShipError catch


### FINDING_3: Pre-merge gate must not stall on skip
- **Reviewer(s)**: Cursor-dyn-Workflow Gate Integrator
- **Severity**: minor
- **Concern**: `_premerge_main_health_gate()` needs an explicit `skip` terminal branch; otherwise the new status falls through to the STALLED path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Workflow Gate Integrator: In ship.py plan bullet, require explicit if health.status == "skip": return None before the terminal stall branch


### FINDING_4: Post-merge gate must not stall on skip
- **Reviewer(s)**: Cursor-dyn-Workflow Gate Integrator
- **Severity**: minor
- **Concern**: `_postmerge_main_health_gate()` likewise needs to treat `skip` as terminal, or post-merge runs will stall on the default-branch CI health detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Workflow Gate Integrator: In ship.py plan bullet, require explicit if health.status == "skip": return None alongside pass before the stall branch


