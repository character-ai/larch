### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_launch_review.py:23-50
- **Concern**: Item 2 assumes raising inner `--timeout` fixes the flake, but `_run` already bounds the whole CLI with `subprocess.run(..., timeout=60)` and documents cold-start spikes as an outer `TimeoutExpired` risk separate from the inner `--timeout` arg. Scenario: If the observed failure was outer `subprocess.TimeoutExpired` on `_run`, changing success-path literals from `"2"` to `STUB_AGENT_TIMEOUT="20"` leaves the 60s outer cap unchanged and Item 2 can still flake under suite load
- **Proposed resolution**: Record which timeout fired in the original failure (outer `_run` vs inner agent kill in `.diag`/meta) before landing the change; if outer, raise `_run`'s `timeout=60` or add a targeted retry/mark-flaky instead of only widening inner CLI timeout

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_launch_review.py:642-644,1333-1338
- **Concern**: Plan does not warn that retry-counter assertions use the literal `"2"` adjacent to the `_run` timeout pairs being edited. Scenario: An implementer doing a broad `"2"` → `STUB_AGENT_TIMEOUT` replace can break `assert state.read_text().strip() == "2"` in transient/empty-result retry tests while chasing timeout literals
- **Proposed resolution**: Keep replacements scoped to the `--timeout` argv pair only; add an explicit note that `"2"` in assertion/state-file expectations must stay untouched

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_launch_review.py:23-50
- **Concern**: Item 2 raises inner `--timeout` from 2s to 20s but the documented flake axis is `_run`'s outer `subprocess.run(..., timeout=60)` racing cli.py/agents.py cold start under serial suite load; inner `--timeout` bounds only the vendor stub child inside `run_external_agent`, not import/auth/preflight before `Popen`. Scenario: The reported `test_codex_launch_does_not_leak_openai_api_key` timeout during `make py-test` can still hit `TimeoutExpired` on the 60s outer cap while every stub completes instantly, so Item 2 may ship without stabilizing Item 2; if a stub hangs, a larger inner timeout waits longer before kill and can increase pressure on the outer 60s cap
- **Proposed resolution**: Revise Item 2: confirm failure was outer `TimeoutExpired` vs inner agent kill, then fix the matching layer (e.g. raise `_run`'s outer cap with a comment tied to suite-load cold start, or a single targeted change to the historically flaky test) instead of replacing ~20 success-path inner `--timeout` literals; drop the hard ban on touching `_run(..., timeout=60)` unless evidence shows inner timeout was the failure
