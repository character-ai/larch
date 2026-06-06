### [Plan Review] FINDING_2

### FINDING_2: Vendor timing guards miss full ambient-env clearing
- **Reviewer(s)**: Codex-Edge, Codex-dyn-timing-env
- **Severity**: important
- **Concern**: The proposed timing guard/prefix coverage for vendor timing rows is incomplete: CI-fix vendor launchers may remain unpinned, and scanner checks for `record-vendor-task`/`timing-report` lines may require only `LARCH_TIMING_SKILL=implement` rather than the full same-line `DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement` prefix. That can let polluted ambient design timing state mis-tag vendor rows while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add the omitted implement timing emitters to the scanner; apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to the CI launchers, or explicitly narrow the invariant so it no longer claims every implement timing call is covered
  - From Codex-dyn-timing-env: For record-vendor-task and timing-report lines, assert the same command line contains both DESIGN_TMPDIR='' and LARCH_TIMING_SKILL=implement; keep mark lines at the skill-only requirement if broader clearing would be scope creep.


### [Plan Review] FINDING_3

### FINDING_3: A3 workflow_path assertion lacks bounded production scope
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The A3 stale-key assertion for `workflow_path` does not define a bounded production path set. A repo-wide or Python-wide grep could false-fail on tests/fixtures, while a too-narrow grep could miss future production reads outside the current Step 2 pair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin an explicit allowlist (e.g. skills/implement/scripts/run-step2-dispatch.sh skills/implement/scripts/step2-implement.sh scripts/implement-bootstrap.sh scripts/ship-pr.sh python/ship.py python/run_logs.py) with test-* and python/test_* excluded


### [Plan Review] FINDING_4

### FINDING_4: Plan B names duplicate or unreachable CI monitor cases
- **Reviewer(s)**: Cursor-dyn-ci-outcomes, Codex-dyn-ci-outcomes
- **Severity**: important
- **Concern**: Plan B still proposes decide-level `error`/`unknown` cases that duplicate existing parity or budget coverage and are not meaningfully reachable through the monitor path. Implementers may add monkeypatched or direct-decision tests instead of new terminal `MonitorResult` evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-ci-outcomes: Drop this candidate; if a status-gather bail is needed at monitor level use the three-consecutive-failure poll path (poll_ci:411-417 → monitor bail→STALLED at ci_monitor.py:1555-1561) already covered at poll_ci in test_ci_monitor.py:330-351
  - From Codex-dyn-ci-outcomes: Revise B to require only genuinely monitor-level tests: runner-backed gh pr view/status-error through monitor asserts Outcome.STALLED and merged PR through monitor asserts Outcome.OK; drop unknown-status fallthrough unless a real monitor-reachable branch is identified


