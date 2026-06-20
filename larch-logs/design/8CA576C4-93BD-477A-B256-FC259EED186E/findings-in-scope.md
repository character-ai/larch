### FINDING_1: Item 2 may fix the wrong timeout layer
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan treats widening success-path inner `--timeout` literals as the fix for `test_codex_launch_does_not_leak_openai_api_key` flake, but `_run` already caps the whole CLI with `subprocess.run(..., timeout=60)` and documents cold-start spikes under serial suite load as a separate outer `TimeoutExpired` risk. Inner `--timeout` bounds only the vendor stub child inside `run_external_agent`, not import/auth/preflight before `Popen`. If the observed failure was outer `TimeoutExpired` on `_run`, replacing `"2"` with a shared generous inner constant leaves the 60s outer cap unchanged and Item 2 may still flake under suite load; if a stub hangs, a larger inner timeout waits longer before kill and can increase pressure on the outer 60s cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Record which timeout fired in the original failure (outer `_run` vs inner agent kill in `.diag`/meta) before landing the change; if outer, raise `_run`'s `timeout=60` or add a targeted retry/mark-flaky instead of only widening inner CLI timeout
  - From Cursor-Pragmatic: Revise Item 2: confirm failure was outer `TimeoutExpired` vs inner agent kill, then fix the matching layer (e.g. raise `_run`'s outer cap with a comment tied to suite-load cold start, or a single targeted change to the historically flaky test) instead of replacing ~20 success-path inner `--timeout` literals; drop the hard ban on touching `_run(..., timeout=60)` unless evidence shows inner timeout was the failure

### FINDING_2: Broad `"2"` replace can break retry-counter assertions
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan does not warn that retry-counter assertions use the literal `"2"` adjacent to the `_run` `--timeout` pairs being edited (e.g. `assert state.read_text().strip() == "2"`). An implementer doing a broad `"2"` → `STUB_AGENT_TIMEOUT` replace can break transient/empty-result retry tests while chasing timeout literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep replacements scoped to the `--timeout` argv pair only; add an explicit note that `"2"` in assertion/state-file expectations must stay untouched

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_launch_review.py:184-1885
- **Concern**: [SCOPE-REDUCTION] Plan broadens the launch-review timeout change from the one observed flaky codex test to most subprocess stub tests. Scenario: The scope anchor identifies only test_codex_launch_does_not_leak_openai_api_key as timing out. Changing unrelated cursor, codex, retry, quota, diagnostics, and cap-hit cases increases changed surface and can make future hung stubs wait for the 60s outer cap instead of the small inner timeout.
- **Proposed resolution**: Limit STUB_AGENT_TIMEOUT use to test_codex_launch_does_not_leak_openai_api_key, or to reproduced flaky launch-review subprocess tests only. Leave unrelated --timeout 2 call sites unchanged.

### FINDING_4:
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

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:35-51; python/test_launch_review.py:184-1663
- **Concern**: [SCOPE-REDUCTION] Plan broadens the launch-review timeout fix from the one scoped flaky test to most vendor-stub subprocess tests. Scenario: The scope anchor names only python/test_launch_review.py::test_codex_launch_does_not_leak_openai_api_key; changing many unrelated cursor, quota, retry, and diagnostics cases is unnecessary churn and weakens the minimum-change contract
- **Proposed resolution**: Narrow the plan to the observed flaky test at python/test_launch_review.py:1563; leave other --timeout "2" subprocess tests unchanged unless they have reproduced the same flake.

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_launch_review.py:177-249,626-693,1104-1335,1451-1666,1811-1886
- **Concern**: [SCOPE-REDUCTION] Plan broadens the timeout fix from the one reported flake to most codex and cursor vendor-stub subprocess tests. Scenario: The issue names only test_codex_launch_does_not_leak_openai_api_key; changing unrelated success, failure, quota, retry, parallel cursor, and cap-hit paths increases churn and weakens short-timeout coverage without being required to close the scoped flake
- **Proposed resolution**: Limit the test_launch_review.py change to the reported test's _run call, with a local comment or narrowly named constant if desired; leave other --timeout "2" literals unchanged unless they are shown to be the same failing case
