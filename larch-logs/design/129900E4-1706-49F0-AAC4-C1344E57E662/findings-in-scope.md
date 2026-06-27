### FINDING_1: Non-directory breadcrumbs source must still fail closed
- **Reviewer(s)**: Codex-Arch, Codex-dyn-Breadcrumb Publish Regression
- **Severity**: blocking
- **Concern**: Relaxing the missing-`breadcrumbs/` path without retaining an explicit non-directory reject lets a breadcrumbs hint that exists as a file (inside an otherwise valid session) derive `source_root = src.parent` and publish quiet logs from the session root instead of failing closed. That weakens source confinement and breaks the documented reject contract (`python/larch/report/run_logs.py:2225-2227`, `SECURITY.md:420-427`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the new missing-directory no-op, but return 1 when `src.exists()` and `not src.is_dir()` before scanning `source_root`; add a regression test for an existing non-directory hint
  - From Codex-dyn-Breadcrumb Publish Regression: Keep the missing-path relaxation, but retain an explicit src.exists() and not src.is_dir() rejection before deriving source_root; add a regression test for a breadcrumbs path that exists as a file.

### FINDING_2: Regression test fixture must create session root before writing quiet log
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-Breadcrumb Publish Regression
- **Severity**: blocking
- **Concern**: `test_publish_breadcrumbs_main_succeeds_without_breadcrumbs_dir` (plan `python/test_run_logs.py:50-55`) never creates the `session` directory before `Path.write_text` on `session/larch-quiet-implement-1.log`. The fixture raises `FileNotFoundError` before the test can verify the missing-`breadcrumbs/` fix; adjacent tests already create parent directories first (`python/test_run_logs.py:2209-2211`, `2228-2230`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `session.mkdir(parents=True)` before writing the quiet log and calling `publish_breadcrumbs_main`
  - From Codex-dyn-Breadcrumb Publish Regression: Add session.mkdir(parents=True) before writing the quiet log, while still leaving session/breadcrumbs absent.

### FINDING_3: Design log-publish still passes wrong breadcrumb source root
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan does not repair the `/design` log-publish source root. `/design` log-publish calls run-log commit with `--log-root` under the disposable worktree, so the proposed publisher derives and scans the worktree parent. Quiet logs live in `DESIGN_TMPDIR`, and the copy loop places them under `larch-logs/design/<run_id>`, so `/design` still commits no `breadcrumbs/quiet.log`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add the narrow design path needed by the issue, such as honoring the documented LARCH_BREADCRUMB_SOURCE_DIR source hint in _publish_breadcrumbs_with_warning and setting it to design_tmpdir/breadcrumbs for the design log-publish run-log commit.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/report/run_logs.py:2225-2227
- **Concern**: [SCOPE-REDUCTION] Narrow the missing-hint guard instead of deleting the whole `src.is_dir()` block. Scenario: SECURITY.md § Breadcrumb stream redaction still lists "source path exists but is not a directory" as a fail-closed reject (rc=1). The plan removes the entire block, so a regular file at the hint path would scan `src.parent` and may publish instead of rejecting. The live `_commit_run` path only needs the missing-directory case to succeed.
- **Proposed resolution**: In `publish_breadcrumbs_main`, replace `if not src.is_dir(): return 1` with `if src.exists() and not src.is_dir(): return 1` (keep the stderr message). That restores publication when `breadcrumbs/` was never created without weakening the documented reject for an existing non-directory hint.

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/report/run_logs.py:2225-2228; SECURITY.md:420-425
- **Concern**: [SCOPE-REDUCTION] Plan removes the entire source-dir is_dir rejection, not just the missing breadcrumbs-dir case.. Scenario: An existing non-directory source hint under a session tmpdir would become valid; publish_breadcrumbs_main would scan the parent and could publish quiet logs, regressing the documented fail-closed contract for source path exists but is not a directory.
- **Proposed resolution**: Reject existing non-directories and allow only absent hints, for example keep a guard that returns 1 when src.exists() and not src.is_dir(), then continue when src is absent.
