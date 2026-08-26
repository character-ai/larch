# scripts/deny-edit-write.sh — contract

`scripts/deny-edit-write.sh` is a token-gated PreToolUse hook used by `/research`, `/audit-umbrella`, `/file-bug`, `/triage`, `/umbrella`, `/complete-umbrella`, and `/debate`. Each consumer passes its skill name as the recognized first argument. The script itself is a thin fail-CLOSED shim: the policy lives in Rust as `larch hook deny-edit-write <token>` (`crates/larch-cli/src/hook_commands.rs`), invoked through `scripts/larch.sh` with `LARCH_BOOTSTRAP_NO_INSTALL=1` so a hook never bootstraps an install inside its timeout. When the larch binary is unavailable (missing `scripts/larch.sh`, no installed binary, or any non-zero exit) the shim emits the fixed read-only-repo deny envelope and exits 0. The Rust verb owns the regression coverage as `#[cfg(test)]` tests in `hook_commands.rs`.

## Activation gate

Before reading stdin, the verb checks `${XDG_CACHE_HOME:-${HOME:-}/.cache}/larch/deny-edit-write-active` for a fresh sentinel named `<token>-*`. Recognized token prefixes are `research`, `audit-umbrella`, `file-bug`, `triage`, `umbrella`, `complete-umbrella`, and `debate`. The TTL is 360 minutes. The filename embeds the writer's `$PPID` for debugging and per-run overwrite only. `/debate`'s sentinel is written by `session setup --deny-edit-write debate`, so its suffix embeds the setup process PID; the other consumers keep their hand-written `<token>-$PPID` fences.

A missing activation directory, unreadable directory, stale sentinel, missing token, or unrecognized token is inactive. Inactive hooks exit 0 with empty stdout. There is no any-sentinel fallback, so a stale tokenless registration cannot be re-armed by another skill's fresh sentinel. The hook performs no `$PPID` correlation because production PreToolUse parent PIDs can diverge from orchestrator Bash parent PIDs.

## Active scratch enforcement

When activation is live, the verb permits the call only when the tool's target path resolves to an absolute path under canonical `/tmp` or the larch cache `sessions/` root. Every other active outcome denies: missing path, relative path, traversal outside either root, symlink cycle, or canonicalization failure.

The verb reads stdin JSON and extracts the target as the first non-empty string of `.tool_input.file_path` then `.tool_input.notebook_path`. NotebookEdit uses `notebook_path`; the length-aware fallback prevents fail-open on an empty `file_path` that shadows a valid `notebook_path`.

Path resolution mirrors `larch hook block-submodule-edit`: bounded symlink walk (max depth 40; cycle means deny), nearest-existing-ancestor probe, then canonicalization to handle macOS `/tmp` to `/private/tmp` aliasing. The allowed roots are canonicalized before comparison. The decision is exact equality or a root-prefix match.

On allow the verb emits empty stdout and exits 0. On deny it emits a fixed-literal `hookSpecificOutput` JSON envelope (single fixed reason string, no runtime interpolation) and exits 0.

The hook is the sole mechanical enforcer of the active scratch-only policy for the matched Claude tool surface. `allowed-tools` declares each orchestrator's surface but does not confine writes; see `docs/security/workflow-trust-and-mutations.md` for the residual-risk framing. `/research` must keep matcher `Edit|Write|NotebookEdit`. The other consumers keep only the Write matchers their prompts declare. `/triage` activates its token only after the initial security, repository-target, and immutable-main gates. Skills that delegate through `Skill` keep that surface outside this path matcher.

Stale or leaked registrations no longer deny by themselves. A fresh activation sentinel is required for each consumer token.
