### [Plan Review] FINDING_5

### FINDING_5: Verification can run before later mutating lint-fix gate
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: `_stage_and_push_ci_fixes` may run `run_checks_with_lint_fix_loop` after `_verify_failed_jobs_locally`. If that later lint-fix changes shared files and regresses an originally failed job, the PR can be pushed without re-running that failed-job verifier after the final mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Move or repeat failed-job verification after the relevant-checks lint-fix gate, and rerun relevant-checks if the verifier itself applies changes before push


### [Plan Review] FINDING_7

### FINDING_7: Return code capture and vendor rc=1 handling are brittle
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-rc-chain-integrity
- **Severity**: nit
- **Concern**: The plan captures `_verify_failed_jobs_locally` via a bare immediate `$?` and leaves vendor rc=1 behavior implicit. Any inserted command can clobber the verifier return code, and the caller lacks an explicit `1|*)` handling path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Capture verify_rc=$? immediately after the call and case on verify_rc; have run_ci_fix_vendor return that value explicitly
  - From Cursor-dyn-rc-chain-integrity: Capture verify_rc=$? right after _verify_failed_jobs_locally; in run_evaluate_failure add explicit 1) arm (ci-local-unfixable / generic failure) before esac


### [Plan Review] FINDING_12

### FINDING_12: vendor_rc variable can be unset if branches are unified later
- **Reviewer(s)**: Cursor-dyn-rc-chain-integrity
- **Severity**: nit
- **Concern**: `vendor_rc` is local enough for the current `gh_logs_rc=0` branch, but it is unset on the other vendor path. If later refactoring reads it across unified branches, the value handling becomes brittle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-rc-chain-integrity: Initialize vendor_rc= at loop top or only read vendor_rc inside each branch that sets it

