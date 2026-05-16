# lib-external-launcher-common.sh

Exposes:

- `external_launcher_promote_inner_done <output_path>` — atomically renames `${output_path}.inner.done` to `${output_path}.done` when present, signaling that launcher-owned post-processing has completed.
- `external_launcher_append_outer_meta <meta_path> <outer_launcher_path> <prompt_file_sidecar> <workdir> [risk]` — appends `OUTER_LAUNCHER=…`, `OUTER_LAUNCHER_PROMPT_FILE=…`, `OUTER_LAUNCHER_WORKDIR=…`, and `OUTER_LAUNCHER_RISK=high|low` to an existing `.meta` sidecar so `collect-agent-results.sh` can replay empty-output retries through the originating launcher with the same risk-gated effort setting; no-op when the meta file does not yet exist. Missing or invalid risk values are recorded as `high` (fail-closed).
- `external_serial_lock_release_after <lock> <delay>` — schedules a disowned delayed `rmdir` for an acquired lock. Spawn sites pass `LARCH_EXTERNAL_SERIAL_LOCK_DELAY` (default 0.5) so the lock covers CLI startup without holding it for the whole run.
- `external_auth_verdict <tool> <sidecar> [sidecar...]` — prints `auth` when any readable sidecar matches the auth classifier, `non-auth` when at least one sidecar is readable but none match, and `unclassified` when no sidecar is readable. Cursor callers pass both the wrapper sidecar and `.diag` file because stderr can land in either place depending on capture mode.

The library is sourced-only (no shebang, no `set -e`); callers own exit semantics. Loaded once per shell via the `LARCH_LIB_EXTERNAL_LAUNCHER_COMMON_LOADED` guard so the per-tool wrapper libs (`lib-codex-launcher-common.sh`, `lib-cursor-launcher-common.sh`) can both source it without double-defining functions.

The per-tool wrappers (`codex_launcher_promote_inner_done`, `codex_launcher_append_outer_meta`, `cursor_launcher_promote_inner_done`, `cursor_launcher_append_outer_meta`) are thin one-line aliases retained in their respective per-tool libs so existing call sites in `launch-review.sh --tool codex`, `launch-review.sh --tool cursor`, and `launch-cursor-implement.sh` continue to work unchanged.
