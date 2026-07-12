### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py:141-175
- **Concern**: Specify backlog-nudge `ShipError` coercion alongside preflight. Scenario: The plan names only the concurrency preflight probe for degraded issue-list failure (`ShipError` -> `[]`). `_bugs_backlog_nudge_issue_rows` uses a different contract today: command or JSON failure returns `None` with stderr, then `bugs_backlog_nudge_main` exits `1` (`test_bugs_backlog_nudge_fails_clearly_on_gh_failure`). `issue_list_read` raises `ShipError` instead of returning a failing `CommandResult`, so an uncaught wrapper error would traceback instead of preserving the advisory failure exit and stderr grammar.
- **Proposed resolution**: In `audit_runs.py` plan text, add an explicit backlog-nudge rule: catch `ShipError` (and preserve the existing invalid-JSON stderr) inside `_bugs_backlog_nudge_issue_rows`, return `None`, and keep exit `1` behavior. Extend `test_audit_runs.py` wrapper mocks to assert that path, not only preflight empty-list coercion.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/git/gh.py:197-205; python/larch/issue/audit_runs.py:141-170; python/larch/issue/combine_issues.py:675-705; python/larch/issue/deps_audit.py:256-285
- **Concern**: The plan does not define how callers retain distinct transport and parse failure categories. Scenario: issue_list_read raises ShipError for both command failures and malformed JSON, but callers currently expose different messages or warning codes such as gh_api_failed versus json_invalid
- **Proposed resolution**: Add a typed read/parse distinction or shared classifier, then map each caller’s existing failure contract explicitly and test both paths



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/learn_from_bugs.py:923-938
- **Concern**: learn_from_bugs omits the wrapper fields tuple. Scenario: The UPDATED section only passes search state limit and repo, but build_digest reads body title number closedAt url and state from each row; a minimal fields argument can return rows with empty bodies and silently degrade scan output
- **Proposed resolution**: Add fields=("number","title","body","closedAt","url","state") to the learn_from_bugs plan (mirror combine_issues) and require the same tuple in test_learn_from_bugs wrapper assertions



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_create.py:812-848
- **Concern**: list_issues_main must keep exit 0 on read failure. Scenario: The section lists LIST_STATUS preservation but not exit code; uncaught ShipError or return 1 would break the established failed-but-zero contract enforced by test_list_issues_missing_gh_emits_failed
- **Proposed resolution**: State that ShipError translation in list_issues_main emits LIST_STATUS=failed plus warnings and returns 0; add an explicit exit-code assertion to the test_issue_create failure rows



