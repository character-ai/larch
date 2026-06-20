### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_launch_review.py:23-50
- **Concern**: Item 2 assumes raising inner `--timeout` fixes the flake, but `_run` already bounds the whole CLI with `subprocess.run(..., timeout=60)` and documents cold-start spikes as an outer `TimeoutExpired` risk separate from the inner `--timeout` arg. Scenario: If the observed failure was outer `subprocess.TimeoutExpired` on `_run`, changing success-path literals from `"2"` to `STUB_AGENT_TIMEOUT="20"` leaves the 60s outer cap unchanged and Item 2 can still flake under suite load
- **Proposed resolution**: Record which timeout fired in the original failure (outer `_run` vs inner agent kill in `.diag`/meta) before landing the change; if outer, raise `_run`'s `timeout=60` or add a targeted retry/mark-flaky instead of only widening inner CLI timeout



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



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_launch_review.py:642-644,1333-1338
- **Concern**: Plan does not warn that retry-counter assertions use the literal `"2"` adjacent to the `_run` timeout pairs being edited. Scenario: An implementer doing a broad `"2"` → `STUB_AGENT_TIMEOUT` replace can break `assert state.read_text().strip() == "2"` in transient/empty-result retry tests while chasing timeout literals
- **Proposed resolution**: Keep replacements scoped to the `--timeout` argv pair only; add an explicit note that `"2"` in assertion/state-file expectations must stay untouched



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_launch_review.py:177-1888
- **Concern**: [SCOPE-REDUCTION] Plan expands the timeout change across many unrelated launch-review tests. Scenario: The issue names only test_codex_launch_does_not_leak_openai_api_key, but the plan changes broad success, retry, quota, diagnostics, parallel, and cap-hit cases. That adds scope and can hide unrelated future slowdowns.
- **Proposed resolution**: Limit STUB_AGENT_TIMEOUT usage to python/test_launch_review.py:1544-1571 for test_codex_launch_does_not_leak_openai_api_key, or only the smallest set with observed timeout evidence. Leave unrelated --timeout 2 literals unchanged.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_launch_review.py:23-50
- **Concern**: Item 2 raises inner `--timeout` from 2s to 20s but the documented flake axis is `_run`'s outer `subprocess.run(..., timeout=60)` racing cli.py/agents.py cold start under serial suite load; inner `--timeout` bounds only the vendor stub child inside `run_external_agent`, not import/auth/preflight before `Popen`. Scenario: The reported `test_codex_launch_does_not_leak_openai_api_key` timeout during `make py-test` can still hit `TimeoutExpired` on the 60s outer cap while every stub completes instantly, so Item 2 may ship without stabilizing Item 2; if a stub hangs, a larger inner timeout waits longer before kill and can increase pressure on the outer 60s cap
- **Proposed resolution**: Revise Item 2: confirm failure was outer `TimeoutExpired` vs inner agent kill, then fix the matching layer (e.g. raise `_run`'s outer cap with a comment tied to suite-load cold start, or a single targeted change to the historically flaky test) instead of replacing ~20 success-path inner `--timeout` literals; drop the hard ban on touching `_run(..., timeout=60)` unless evidence shows inner timeout was the failure



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



