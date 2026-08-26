# scripts/sessionstart-statusline.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/sessionstart-statusline.sh` is the thin SessionStart shim for the Rust-owned `larch hook sessionstart-statusline` verb.

The shim enters the verified `scripts/larch.sh` bootstrap with `LARCH_BOOTSTRAP_NO_INSTALL=1`. If that runtime is unavailable or the verb fails, the shim exits 0 with no stdout or stderr.

The Rust owner reads the SessionStart payload once and idempotently installs the larch progress statusline for the current clone. It preserves these contracts:

- clear a stale active-run pointer only for `startup` and `clear`; preserve it for `resume` and `compact`;
- skip reset while a live larch bgjob exists for the clone;
- delete only `~/.cache/larch/progress/<clone-hash>/current`, preserving run directories and `breadcrumbs.log`;
- mutate only `~/.cache/larch/statusline.sh`, `<repo>/.claude/settings.local.json`, and that clone-local pointer;
- honor `LARCH_STATUSLINE_DISABLE=1` and `LARCH_STATUSLINE_REFRESH_SECONDS`;
- refuse symlinked target paths or ancestors;
- make no network calls and emit no hook output.

Rust tests in `crates/larch-cli/src/progress_commands.rs` cover reset-before-install ordering from one payload.
