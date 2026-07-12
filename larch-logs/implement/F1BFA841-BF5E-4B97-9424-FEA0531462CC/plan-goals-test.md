## Goal
Implement issue #7053: [IMPLEMENTING] contract-unification [FEATURE] repoint issue view/edit/close raw-argv to gh wrappers.

## Implementation Plan
## Plan

### Approach

- Replace each scoped raw `gh issue view`, `edit`, and `close` invocation with its existing typed wrapper.
- Pass `proc` or `proc.ProcRunner()` through the wrapper seam.
- Let `_retry_read` govern transient reads. Remove caller-owned read retries and mutation retries.
- Preserve existing output files, redaction, status KVs, sentinels, and failure messages.
- Keep raw label creation unchanged. Do not modify `python/larch/git/gh.py` or runner-level fixtures that already validate canonical argv.

### Production files

### UPDATED: python/larch/design/design_step0.py
Use `gh.issue_view_field_read` in `_read_json_issue`. Remove its unconditional subprocess retry loop and sleep while preserving JSON parsing and clarification-label detection.

### UPDATED: python/larch/design/design_terminal.py
Use `gh.issue_close` and `gh.issue_view_field_read` during recovered-report reconciliation. Preserve close verification, comment idempotency, and existing failure details.

### UPDATED: python/larch/design/decompose.py
Use `gh.issue_close` for the original partitioned issue. Remove the local close retry wrapper because mutations must not retry implicitly. Preserve the posted-comment sentinel on close failure.

### UPDATED: python/larch/design/design_oos.py
Call `gh.issue_label_add` directly for high-risk OOS issues. Retain `_run_gh` only for label creation and preserve pending-label retry state.

### UPDATED: python/larch/state/bootstrap.py
Import `gh` and `proc`, then use `gh.issue_view_template_read` for feature-description materialization. Rename the existing command-result binding to `view_result` so it cannot collide with the imported `gh` module; write `view_result.stdout` and stderr to the existing artifacts. Preserve fork repository selection, stderr logging, and failure markers.

### UPDATED: python/larch/state/admission.py
Replace `_gh_issue_view` raw calls with `gh.issue_view_field_read`. Remove the local retry-all-errors behavior and retain the admission result grammar.

### UPDATED: python/larch/issue/issue_create.py
Use `gh.issue_view_field_read` for external issue details and `gh.issue_close` for orphan rollback and cleanup. Preserve warnings, redacted errors, and cleanup KVs.

### UPDATED: python/larch/issue/_oos.py
Import `gh` and `proc`, then use `gh.issue_view_field_read` for targeted filed-issue enrichment. Preserve fetch-failure stubs and invalid-JSON handling.

### UPDATED: python/larch/issue/audit_runs.py
Use `gh.issue_view_field_read` when resolving the prior audit range and `gh.issue_close` when closing superseded reports. Keep partial-success reporting unchanged.

### UPDATED: python/larch/issue/deps_audit.py
Use `gh.issue_edit_body_file` for sanitized body rewrites and `gh.issue_close` for planned closures. Preserve temporary-file cleanup and redacted failure reporting.

### UPDATED: python/larch/issue/combine_issues.py
Use `gh.issue_close` for combined-away and stale issues. Remove the bespoke close retry loop while preserving comments, reasons, warning redaction, and close counts.

### UPDATED: python/larch/issue/oos_priority.py
Delete `label_edit_argv`. Keep `label_create_argv` unchanged because label creation is outside this migration.

### UPDATED: python/larch/issue/oos_filer.py
Call `gh.issue_label_add` directly for priority labels. Keep raw label creation isolated behind the existing helper and preserve durable retry metadata on failure.

### UPDATED: python/larch/calibration/difficulty.py
Use `gh.issue_label_remove` and `gh.issue_label_add` for difficulty labels. Keep label creation unchanged and preserve the `STATUS`, `WARNING`, and `ERROR` envelope.

### UPDATED: python/larch/implement/preflight.py
Import `gh` and `proc`, then use `gh.issue_view_field_read`. Persist the returned stdout and stderr to the existing preflight artifacts and remove the direct second subprocess attempt.


## Test plan
