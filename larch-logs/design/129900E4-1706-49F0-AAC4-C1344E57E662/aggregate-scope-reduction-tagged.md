### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/report/run_logs.py:2225-2227
- **Concern**: [SCOPE-REDUCTION] Narrow the missing-hint guard instead of deleting the whole `src.is_dir()` block. Scenario: SECURITY.md § Breadcrumb stream redaction still lists "source path exists but is not a directory" as a fail-closed reject (rc=1). The plan removes the entire block, so a regular file at the hint path would scan `src.parent` and may publish instead of rejecting. The live `_commit_run` path only needs the missing-directory case to succeed.
- **Proposed resolution**: In `publish_breadcrumbs_main`, replace `if not src.is_dir(): return 1` with `if src.exists() and not src.is_dir(): return 1` (keep the stderr message). That restores publication when `breadcrumbs/` was never created without weakening the documented reject for an existing non-directory hint.

### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/report/run_logs.py:2225-2228; SECURITY.md:420-425
- **Concern**: [SCOPE-REDUCTION] Plan removes the entire source-dir is_dir rejection, not just the missing breadcrumbs-dir case.. Scenario: An existing non-directory source hint under a session tmpdir would become valid; publish_breadcrumbs_main would scan the parent and could publish quiet logs, regressing the documented fail-closed contract for source path exists but is not a directory.
- **Proposed resolution**: Reject existing non-directories and allow only absent hints, for example keep a guard that returns 1 when src.exists() and not src.is_dir(), then continue when src is absent.
