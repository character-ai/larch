# test-cleanup.sh

Standalone offline regression harness for `/cleanup` age-based session directory pruning and dangling `current-design-env-*.sh` symlink reaping.

The harness runs `skills/cleanup/scripts/cleanup.sh` with `XDG_CACHE_HOME` pointed at a temporary directory so no host `~/.cache/larch/sessions/` state is touched. To keep the harness offline and fast when the host `/tmp` tree is large, it points the production script at a private `LARCH_TEST_TMP_ROOT` fixture for the `/tmp` pattern scan (defaulting to `/tmp` when unset). Session directory mtimes are seeded with `touch -t` (`200001010000` for stale fixtures, `209901010000` for fresh activity). A PATH-local `pgrep` stub exercises multi-process detection without requiring real `claude` processes.

Covered cases:

- **multiple-claude-no-abort**: stub `pgrep -x claude` reports three PIDs; cleanup exits 0 and emits `SESSION_COUNT=3` (informational only — no singleton abort)
- **stale-dir-removed**: session directory with stale mtime (newest activity before retention cutoff) is deleted; `CACHE_REMOVED=1`
- **fresh-dir-kept**: session directory with recent mtime is retained; `CACHE_REMOVED=0`
- **stale-dir-with-keepalive-kept**: stale session directory that still carries `.larch-keepalive` is retained; `CACHE_REMOVED=0`
- **symlinked-session-dir-skipped**: top-level session entry that is a symlink to another tree is not traversed with `rm -rf`; `CACHE_REMOVED=0`
- **stale-with-fresh-depth1-child**: stale session root mtime but a fresh file at depth 1; directory kept because `newest_activity_mtime` scans `find -mindepth 1 -maxdepth 5`
- **stale-with-fresh-depth2-grandchild**: stale ancestors with a fresh file at depth 2; directory kept
- **stale-with-fresh-depth4-manifest**: stale ancestors with fresh `larch-logs/implement/<RUN_ID>/manifest.json` at depth 4 from the session root; directory kept
- **stale-with-fresh-depth5-round**: stale ancestors with fresh `larch-logs/implement/<RUN_ID>/round-1/findings.md` at depth 5 from the session root (implement run-log round artifact boundary); directory kept
- **invalid-retention-fallback**: `LARCH_CLEANUP_RETENTION_DAYS=abc` emits a stderr warning and falls back to 7 days; a stale session dir is still removed under the fallback
- **dangling-symlink-reaped**: broken `current-design-env-test.sh` symlink in the sessions parent (`-L` and `! -e`) is removed; `SYMLINKS_REMOVED=1`
- **live-symlink-kept**: `current-design-env-*.sh` symlink pointing at an existing file is retained; `SYMLINKS_REMOVED=0`
- **stale-tmp-dir-removed**: stale `claude-implement-*` directory under `LARCH_TEST_TMP_ROOT` is deleted; `TMP_REMOVED=1`
- **stale-tmp-file-removed**: stale loose file matching a `/tmp` pattern (e.g. `larch4-review.diff`) under `LARCH_TEST_TMP_ROOT` is deleted; `TMP_REMOVED=1`
- **date-failure-errors**: `date +%s` failure exits non-zero with a loud stderr error instead of silently disabling deletion
- **find-failure-skips-deletion**: `find` failure while scanning an entry warns and keeps the directory rather than misclassifying it stale

Stdout contract under test: `SESSION_COUNT`, `CACHE_REMOVED`, `TMP_REMOVED`, and `SYMLINKS_REMOVED` (`emit_kv` lines). Retention default and validation match `parse_retention_days` in `cleanup.sh` (default 7; positive integer required, otherwise warn and use 7).

Edit in sync: update this harness, `cleanup.sh`, `cleanup.md`, `skills/cleanup/SKILL.md`, and `Makefile` when changing age-based session pruning, retention parsing, symlink reaping, or the depth-5 activity scan boundary.
