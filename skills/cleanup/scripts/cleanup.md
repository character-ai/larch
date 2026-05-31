# cleanup.sh — Contract

**Purpose**: Remove stale larch session temp directories by age and reap dangling `/design` session-env symlinks. Called by `/cleanup` Step 1.

**Primary callers**: `skills/cleanup/SKILL.md` Step 1.

**Invariants**:
- Always runnable: `pgrep -x claude` count is emitted for operator visibility only; the script never aborts because multiple Claude processes are running.
- Age-based retention: removes entries under `${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions/` and matching `/tmp` larch patterns when no file within a bounded nested-activity scan was modified inside the retention window (`LARCH_CLEANUP_RETENTION_DAYS`, default 7). Invalid env values warn on stderr and fall back to 7. Retention uses `find -mtime` 24-hour blocks (platform rounding applies at block boundaries). The cache pass enumerates all non-symlink top-level entries with no age pre-filter and deletes a directory only when `find -maxdepth 5 -mtime -N` finds no file modified within the window; the `/tmp` pass pre-filters top-level entries by `-mtime +N` plus larch name patterns, then applies the same nested confirm for directories. A directory with fresh deep activity (within five levels) is retained even when its top-level mtime is stale.
- Depth-bound tradeoff: the nested scan uses `maxdepth 5`; activity nested deeper than five levels does not protect the directory from removal.
- Nested-scan find-failure fail-safe: when the per-entry `find -maxdepth 5` scan exits non-zero, emit an `larch_err` warning and skip deletion for that entry only (cleanup still exits 0).
- Enumeration-pass fail-open: a failed top-level enumeration `find` is swallowed — the pass exits 0 with counts at 0 and emits no warning.
- Top-level enumeration: neither pass deletes through a symlink (`! -type l`).
- Reaps broken `current-design-env-*.sh` symlinks in the sessions parent (`-type l` and `! -e`).
- Uses bash 3.2-compatible `while IFS= read -r -d $'\0'` — not `mapfile`.

**Outputs** (stdout, KEY=value):
- `SESSION_COUNT=<N>` — number of `claude` processes detected (informational).
- `CACHE_REMOVED=<N>` — count of stale entries removed from the cache dir.
- `TMP_REMOVED=<N>` — count of stale `/tmp` entries removed.
- `SYMLINKS_REMOVED=<N>` — count of dangling `current-design-env-*.sh` symlinks removed.

**Edit-in-sync**: when adding a new `/tmp` pattern, update the `TMP_PATTERNS` array in `cleanup.sh`. Update `skills/cleanup/SKILL.md`, `docs/configuration-and-permissions.md` (`LARCH_CLEANUP_RETENTION_DAYS`), `SECURITY.md` (cleanup retention / enumeration trust boundary), and `skills/cleanup/scripts/test-cleanup.sh` when changing retention, bounded nested-activity / `maxdepth 5` retention (and find-failure fail-safe when that path changes), or symlink reaping.
