# scripts/cleanup-sessionstart.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-sessionstart.sh` is the thin SessionStart shim for the Rust-owned `larch hook cleanup-sessionstart` verb. It is registered for `startup|resume|clear|compact` in `hooks/hooks.json`.

The shim enters the verified `scripts/larch.sh` bootstrap with `LARCH_BOOTSTRAP_NO_INSTALL=1`. If that runtime is unavailable or the verb fails, the shim exits 0 with no stdout or stderr.

The Rust owner first runs `scripts/larch.sh bgjob reap` synchronously, then launches `scripts/larch.sh cleanup run` as a detached child. Both nested calls preserve `LARCH_BOOTSTRAP_NO_INSTALL=1`. The hook exits without waiting for the age-based cleanup sweep, which includes `larch-report-tokens.*` roots retained for advertised `/report-tokens` artifacts.

Cleanup output goes to a newly created, owner-only `${TMPDIR:-/tmp}/larch-cleanup-sessionstart-<pid>.log`. Existing files and symlinks are never reused. The hook emits no advisory JSON and removes the test-only `LARCH_TEST_TMP_ROOT` variable before launching cleanup.

Rust tests in `crates/larch-cli/src/hook_commands.rs` cover command ordering, detachment, log creation, and environment handling.
