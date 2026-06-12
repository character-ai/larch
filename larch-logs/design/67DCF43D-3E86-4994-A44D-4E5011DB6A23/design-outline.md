## Proposed Design Outline

### Goals
- Prevent misclassified launch failures when `LAUNCHER_EXIT` is absent on non-zero process exit.
- Replace all prose `BAIL_REASON` values in `ci-wait.sh` and `ci_monitor.py` with normalized tokens.
- Fix stall-recovery-report.sh: verify legacy-guard correctness, fix multi-line KV encoding, clear stale stall-tracking layers, and consolidate the Tier B bail-token union.

### Non-goals
- No changes to the stall-recovery-report allowlist format or contract `.md`.
- No new CI monitoring features or stall-classification logic changes.
- No changes to `ci-decide.sh` (its tokens are already normalized).

### Approach sketch
- `agents.py`: add `process_rc` parameter to `parse_launcher_exit_text`; return `max(process_rc, 1)` when `LAUNCHER_EXIT=` is missing and process exited non-zero; update all callers.
- `ci-wait.sh` + `ci_monitor.py`: replace 5 prose strings with tokens `poll-budget-exhausted`, `ci-wait-unexpected-exit`, `no-ci-checks-observed`, `ci-status-stale`, `ci-decide-error`; add each token to `runtime_bail_token_lines()` in `stall-recovery-report.sh`.
- `stall-recovery-report.sh normalize-issue-env`: strip embedded newlines before emitting KV output.
- `stall-recovery-report.sh normalize-outcome`: audit the 4 `STALL_TRACKING` read layers; add clear-stall invocation before reporting escalation success.
- `config.py`: add the new 5 bail tokens as constants; update `runtime_bail_token_lines()` to derive them from the single Python source.

### Surfaces in scope
- `python/agents.py` (Item 1)
- `scripts/ci-wait.sh` (Item 2)
- `python/ci_monitor.py` (Item 2)
- `skills/implement/scripts/stall-recovery-report.sh` (Items 2, 3, 4, 5)
- `python/config.py` (Item 5 canonical source)
- `python/test_agents.py`, `skills/implement/scripts/test-stall-recovery-report.sh` (tests)

### Open questions
- None.
