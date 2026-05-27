### DECISION_1: Codex stdin guard mechanism
- **Chosen**: Redirect Codex subprocess stdin to `/dev/null` at the `lib-codex-launcher-common.sh` layer (simpler, robust against parent-shell exit, minimal blast-radius).
- **Alternative**: `setsid` (or `exec setsid`) session detach so Codex runs in its own session and survives parent shell exits regardless of stdin state.
- **Tension**: stdin redirection is a one-line shell change and handles the documented "stdin is closed for this session" error directly. `setsid` is a broader semantic change — it detaches the Codex process from the orchestrator's controlling terminal, which may affect: (a) signal propagation (SIGTERM on timeout still works via process group), (b) macOS vs Linux portability (BSD `setsid` lacks Linux options), (c) any future Codex interactive features that depend on a stdin tty. Codex-Innovation suggested the pty/setsid path; Codex-Pragmatic suggested the simpler stdin guard.
- **Impact**: High — this fix lands in a shared launcher used by every background Codex invocation (voters, reviewers, implementer, research).
- **Affected files**: `scripts/lib-codex-launcher-common.sh`, `scripts/launch-review.sh` (Codex branch), `scripts/launch-codex-implement.sh`, `scripts/run-external-agent.sh` (if the redirect must be enforced at the spawn wrapper layer instead of the launcher).

### DECISION_2: Voter `.done` wait granularity
- **Chosen**: Wait for ALL voter `.done` sentinels in one `wait-for-reviewers.sh` invocation, immediately before tally consumes the outputs (placed in `dispatch-code-voters.sh` just before parse-rate checks).
- **Alternative**: Wait per launch group — one wait after `launch-claude-review.sh` returns (Claude voter only), then a second wait after `dispatch-with-waterfall.sh` returns (Codex + Cursor voters together).
- **Tension**: Single wait is simpler and the natural ergonomic location (matches the tally callsite). Per-group wait surfaces a hung voter faster and isolates timeout failure to the right slot, but adds another moving part and currently the launchers already block. Pragmatic sketch leans single-wait; nothing strongly argues for per-group.
- **Impact**: Medium — affects code-path readability and failure-mode granularity, not correctness.
- **Affected files**: `scripts/dispatch-code-voters.sh`.
