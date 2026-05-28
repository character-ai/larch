## Proposed Design Outline

### Goals
- Eliminate O(n²) heredoc-body lookup that `line_is_heredoc_body_idx` performs on every call inside the three monitor_rc helpers.
- Stop the blanket `# lint-foreground-markers: ok` at the writer-invocation line from silencing all three new monitor_rc checks (init, capture, branching).

### Non-goals
- Migrate the ~5 existing bare suppressions to a scoped form (Round 1: bare keeps "suppress all" semantics).
- Refactor unrelated hotspots in `scripts/lint-foreground-markers.sh`.
- Change the linter exit-code contract or the public banner / per-anchor comment grammar.

### Approach sketch
- Build a per-fence heredoc-body lookup once (bash 3.2-safe), then have the helper loops consult it in O(1) instead of restarting at index 0.
- Replace the blanket early-return in `fence_has_family_b_pid_capture_and_wait` with per-check gating: bare suppression keeps suppressing the legacy token/PID/wait checks; the three new monitor_rc checks honor only an explicit scoped token.
- Extend `scripts/test-lint-foreground-markers.sh` with fixtures for the perf invariant, the bare-suppression no-longer-silences-monitor_rc semantics, and the new scoped tokens.

### Surfaces in scope
- `scripts/lint-foreground-markers.sh`
- `scripts/lint-foreground-markers.md`
- `scripts/test-lint-foreground-markers.sh`
- `scripts/test-lint-foreground-markers.md`
- `BASH_AUTHORING.md` §4 (suppression-grammar prose only)

### Open questions
- Exact scoped-token grammar (e.g. `ok monitor_rc_init,monitor_rc_capture` vs `ok-check=monitor_rc_init`). Step 2b owns the final shape.
