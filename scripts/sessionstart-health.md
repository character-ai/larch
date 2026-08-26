# scripts/sessionstart-health.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/sessionstart-health.sh` is the thin SessionStart shim for the Rust-owned `larch hook sessionstart-health` verb. The hook is advisory and always exits 0.

The shim enters the verified `scripts/larch.sh` bootstrap with `LARCH_BOOTSTRAP_NO_INSTALL=1`. If that runtime is unavailable, the shim emits no output except for the historical stripped-`PATH` fallback: when `jq` is unavailable, it writes one fixed JSON advisory for missing `jq`, or for both missing `jq` and `git`. Those literals contain no interpolated input.

The Rust owner reads the SessionStart payload once and probes:

- availability of `jq` and `git` on `PATH`;
- warn-only drift from the `.claude-plugin` sparse cone in the local larch marketplace;
- dirty worktree state, larch-managed stashes, interrupted Git operations, local branches not merged into `main`, and `.git/larch-stalled-run.txt`;
- an unresolved post-`/review` boundary in the active `/implement` run.

Git repository reads use the shared `GixRepository` adapter. Active-run lookup uses the in-process session resolver and binds a non-empty payload `session_id`; it does not inherit a stale session ID. Missing payload fields, malformed input, probe errors, and absent run state fail open.

When there is no advisory, the hook has no stdout. Otherwise it emits the existing SessionStart `hookSpecificOutput.additionalContext` envelope. Rust unit tests in `crates/larch-cli/src/hook_commands.rs` cover the exact envelopes and each advisory probe.
