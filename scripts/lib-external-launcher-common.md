# lib-external-launcher-common.sh

Sourced-only helper library carrying the canonical launcher mechanics shared between Cursor, Codex, and Gemini external implementer / reviewer launchers. Resolves the byte-equivalent duplication that previously lived independently in `scripts/lib-codex-launcher-common.sh` and `scripts/lib-cursor-launcher-common.sh` (issue #1502).

Exposes:

- `external_launcher_promote_inner_done <output_path>` — atomically renames `${output_path}.inner.done` to `${output_path}.done` when present, signaling that launcher-owned post-processing has completed.
- `external_launcher_append_outer_meta <meta_path> <outer_launcher_path> <prompt_file_sidecar> <workdir> [risk]` — appends `OUTER_LAUNCHER=…`, `OUTER_LAUNCHER_PROMPT_FILE=…`, `OUTER_LAUNCHER_WORKDIR=…`, and `OUTER_LAUNCHER_RISK=high|low` to an existing `.meta` sidecar so `collect-agent-results.sh` can replay empty-output retries through the originating launcher with the same risk-gated effort setting; no-op when the meta file does not yet exist. Missing or invalid risk values are recorded as `high` (fail-closed).
- `external_serial_lock_acquire <out_var> <tool>` — Darwin-only `/tmp/larch-<tool>-serial-${USER:-larch}.lock` `mkdir` lock for `cursor`, `codex`, and `gemini` startup serialization. It recovers stale lock directories older than `LARCH_EXTERNAL_SERIAL_LOCK_TTL` seconds (default 30) and fails open after `LARCH_EXTERNAL_SERIAL_LOCK_TRIES` attempts spaced at 0.1 s (default 300). `LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME` overrides `uname -s` for tests.
- `external_serial_lock_release_after <lock> <delay>` — schedules a disowned delayed `rmdir` for an acquired lock. Spawn sites pass `LARCH_EXTERNAL_SERIAL_LOCK_DELAY` (default 0.5) so the lock covers CLI startup without holding it for the whole run.
- `external_is_auth_failure <tool> <sidecar>` — grep-based classifier for auth/startup failures eligible for the outer retry loop. Cursor includes the verified keychain race signature and macOS `security` CLI exit signature; Codex and Gemini patterns are a defensive net because their exact startup auth strings vary by install. Spawn sites cap attempts with `LARCH_EXTERNAL_AUTH_RETRIES` (default 5).
- `external_auth_verdict <tool> <sidecar> [sidecar...]` — prints `auth` when any readable sidecar matches the auth classifier, `non-auth` when at least one sidecar is readable but none match, and `unclassified` when no sidecar is readable. Cursor callers pass both the wrapper sidecar and `.diag` file because stderr can land in either place depending on capture mode.

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED` guard so the per-tool wrapper libs (`lib-codex-launcher-common.sh`, `lib-cursor-launcher-common.sh`) can both source it without double-defining functions.

The per-tool wrappers (`codex_launcher_promote_inner_done`, `codex_launcher_append_outer_meta`, `cursor_launcher_promote_inner_done`, `cursor_launcher_append_outer_meta`) are thin one-line aliases retained in their respective per-tool libs so existing call sites in `launch-review.sh --tool codex`, `launch-review.sh --tool cursor`, and `launch-cursor-implement.sh` continue to work unchanged.

**Edit-in-sync**: `scripts/lib-codex-launcher-common.sh`, `scripts/lib-cursor-launcher-common.sh`, `scripts/launch-review.sh`, `scripts/launch-cursor-*.sh`, `scripts/launch-codex-*.sh`, `scripts/launch-gemini-implement.sh`, `scripts/lib-gemini-launcher-review.sh`, and their launcher harnesses.
