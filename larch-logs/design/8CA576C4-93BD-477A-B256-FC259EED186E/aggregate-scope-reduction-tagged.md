### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_launch_review.py:184-1885
- **Concern**: [SCOPE-REDUCTION] Plan broadens the launch-review timeout change from the one observed flaky codex test to most subprocess stub tests. Scenario: The scope anchor identifies only test_codex_launch_does_not_leak_openai_api_key as timing out. Changing unrelated cursor, codex, retry, quota, diagnostics, and cap-hit cases increases changed surface and can make future hung stubs wait for the 60s outer cap instead of the small inner timeout.
- **Proposed resolution**: Limit STUB_AGENT_TIMEOUT use to test_codex_launch_does_not_leak_openai_api_key, or to reproduced flaky launch-review subprocess tests only. Leave unrelated --timeout 2 call sites unchanged.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_launch_review.py:23-50
- **Concern**: [SCOPE-REDUCTION] Plan replaces ~20 per-call `--timeout "2"` literals with `STUB_AGENT_TIMEOUT` even though the binding issue reports only `test_codex_launch_does_not_leak_openai_api_key` as flaky. Scenario: Unnecessary churn across the file; any missed site still flakes while unrelated success-path tests get a 10x timeout bump without demonstrated need
- **Proposed resolution**: Bump stub timeout in one place: e.g. normalize `--timeout "2"` to `STUB_AGENT_TIMEOUT` inside `_run` before `subprocess.run`, or change only the reported test (and any proven co-flakers); drop the long per-test replacement list

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_launch_review.py:177-1888
- **Concern**: [SCOPE-REDUCTION] Plan expands the timeout change across many unrelated launch-review tests. Scenario: The issue names only test_codex_launch_does_not_leak_openai_api_key, but the plan changes broad success, retry, quota, diagnostics, parallel, and cap-hit cases. That adds scope and can hide unrelated future slowdowns.
- **Proposed resolution**: Limit STUB_AGENT_TIMEOUT usage to python/test_launch_review.py:1544-1571 for test_codex_launch_does_not_leak_openai_api_key, or only the smallest set with observed timeout evidence. Leave unrelated --timeout 2 literals unchanged.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35-51; python/test_launch_review.py:184-1663
- **Concern**: [SCOPE-REDUCTION] Plan broadens the launch-review timeout fix from the one scoped flaky test to most vendor-stub subprocess tests. Scenario: The scope anchor names only python/test_launch_review.py::test_codex_launch_does_not_leak_openai_api_key; changing many unrelated cursor, quota, retry, and diagnostics cases is unnecessary churn and weakens the minimum-change contract
- **Proposed resolution**: Narrow the plan to the observed flaky test at python/test_launch_review.py:1563; leave other --timeout "2" subprocess tests unchanged unless they have reproduced the same flake.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_launch_review.py:177-249,626-693,1104-1335,1451-1666,1811-1886
- **Concern**: [SCOPE-REDUCTION] Plan broadens the timeout fix from the one reported flake to most codex and cursor vendor-stub subprocess tests. Scenario: The issue names only test_codex_launch_does_not_leak_openai_api_key; changing unrelated success, failure, quota, retry, parallel cursor, and cap-hit paths increases churn and weakens short-timeout coverage without being required to close the scoped flake
- **Proposed resolution**: Limit the test_launch_review.py change to the reported test's _run call, with a local comment or narrowly named constant if desired; leave other --timeout "2" literals unchanged unless they are shown to be the same failing case
