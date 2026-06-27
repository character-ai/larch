### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/report/run_logs.py:2225-2230
- **Concern**: Dropping the source-directory existence/type check turns malformed breadcrumbs hints into valid publish triggers. Scenario: If a real file or other non-directory sits at `.../breadcrumbs`, the new flow will derive `source_root = src.parent` and commit quiet logs from the session root instead of failing closed, which breaks the documented reject contract
- **Proposed resolution**: Keep the new missing-directory no-op, but return 1 when `src.exists()` and `not src.is_dir()` before scanning `source_root`; add a regression test for an existing non-directory hint

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_run_logs.py:50-58
- **Concern**: `test_publish_breadcrumbs_main_succeeds_without_breadcrumbs_dir` never creates `session` before writing `session/larch-quiet-implement-1.log`. Scenario: The fixture setup raises `FileNotFoundError` before the new regression test can run, so the plan cannot verify the missing-breadcrumbs-dir fix
- **Proposed resolution**: Add `session.mkdir(parents=True)` before writing the quiet log and calling `publish_breadcrumbs_main`

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_log_publish_flow.py:314-336; python/larch/report/run_logs.py:1874-1881
- **Concern**: Plan does not repair the design log-publish source root.. Scenario: /design log-publish calls run-log commit with --log-root under the disposable worktree, so the proposed publisher derives and scans the worktree parent. The quiet logs are in DESIGN_TMPDIR, and the copy loop places them under larch-logs/design/<run_id>, so /design still commits no breadcrumbs/quiet.log.
- **Proposed resolution**: Add the narrow design path needed by the issue, such as honoring the documented LARCH_BREADCRUMB_SOURCE_DIR source hint in _publish_breadcrumbs_with_warning and setting it to design_tmpdir/breadcrumbs for the design log-publish run-log commit.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-Breadcrumb Publish Regression
- **Severity**: blocking
- **Focus area**: security
- **Location**: plan.txt:21-25
- **Concern**: 1) Removing the explicit non-directory source-path reject weakens source confinement.. Scenario: A breadcrumbs hint that already exists as a file inside a valid session would now publish from its parent session root instead of failing closed. Current code rejects non-directory sources at python/larch/report/run_logs.py:2225-2227, and SECURITY.md:420-427 still requires that path shape to be rejected.
- **Proposed resolution**: Keep the missing-path relaxation, but retain an explicit src.exists() and not src.is_dir() rejection before deriving source_root; add a regression test for a breadcrumbs path that exists as a file.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-Breadcrumb Publish Regression
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:50-55
- **Concern**: 2) The new direct-publish regression test cannot set up the quiet log because it never creates the session root before writing session/larch-quiet-implement-1.log.. Scenario: Path.write_text at plan.txt:53 will raise FileNotFoundError unless the parent session directory exists. The current adjacent tests create their parent directory first at python/test_run_logs.py:2209-2211 and 2228-2230.
- **Proposed resolution**: Add session.mkdir(parents=True) before writing the quiet log, while still leaving session/breadcrumbs absent.
