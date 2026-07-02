## Proposed Design Outline

### Goals
- Widen the retry gate in `ci_agentic_fix.py`'s `_run_cycle` so the single bounded retry fires on `launcher_exit == config.EXIT_TIMEOUT` **or** a missing/empty output file, mirroring `_voter_needs_retry` (plan_review_panel.py) and `_needs_diagram_retry` (pr_body.py).
- Make the execution-issues.md retry log entry describe the real triggering condition instead of a hardcoded "(exit 124)".
- Correct the stale in-code comment that already (inaccurately) claims empty-output coverage.

### Non-goals
- No new `.retried`-sidecar mechanism: `_emit_ci_retry_warning` already logs directly to `execution-issues.md` inline at the retry site, so the cross-module sidecar hand-off used by the code-flow diagram lane (needed there because the write happens in a different module than the log call) is not needed here.
- No change to retry count/bounds: stays a single retry per Decision 1 (discussion-round1.md), not the 4-retry code-flow constant.
- No change to the outer `--max-cycles` cycle loop, `_wait_for_ci`, or any other launch site in this file (only one call site matches the bug).

### Approach sketch
- Keep computing `launcher_exit` from the first `agents.launch_tier` call as today.
- Widen the `if launcher_exit == config.EXIT_TIMEOUT:` at ci_agentic_fix.py:521 to also retry when the output file is missing or zero-byte.
- Extend `_emit_ci_retry_warning` to accept the resolved `launcher_exit` so the log entry reflects the real exit code instead of a hardcoded "(exit 124)".
- Update the stale comment above the widened `if` to describe both trigger conditions accurately.

### Surfaces in scope
- `python/larch/implement/ci_agentic_fix.py` (`_run_cycle`, `_emit_ci_retry_warning`)
- `python/tests/implement/test_ci_agentic_fix.py` (new regression test for the empty-output retry path; existing exit-124 retry test stays green)

### Open questions
- None.
