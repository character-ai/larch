# scripts/audit-edit-write.sh — contract

`${CLAUDE_PLUGIN_ROOT}/scripts/audit-edit-write.sh` is the thin PostToolUse shim for the Rust-owned `larch hook audit-edit-write` verb. This dev-only `Edit`/`Write` audit hook ships with the plugin but is not registered by default in `hooks/hooks.json` or `.claude/settings.json`.

The shim enters the verified `scripts/larch.sh` bootstrap with `LARCH_BOOTSTRAP_NO_INSTALL=1`. It has no contract stdout and always exits 0, including when the runtime is unavailable or an append fails.

The Rust owner accepts only a JSON object on stdin and appends its compact representation as one JSONL record to `${CLAUDE_PROJECT_DIR:-<cwd>}/.claude/hook-audit.log`. It refuses a symlinked `.claude` directory and a symlinked, multiply linked, or non-regular audit path. Malformed input and unsafe paths fail open without a write.

See `docs/dev-hook-audit.md` for opt-in, rotation, and privacy guidance and `docs/security/artifacts-redaction-and-publication.md` for artifact classification. Rust tests in `crates/larch-cli/src/hook_commands.rs` cover append, invalid input, and unsafe paths.
