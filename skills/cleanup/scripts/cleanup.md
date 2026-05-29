# cleanup.sh — Contract

**Purpose**: Remove stale larch session temp directories by age and reap dangling `/design` session-env symlinks. Called by `/cleanup` Step 1.

**Primary callers**: `skills/cleanup/SKILL.md` Step 1.

**Invariants**:
- Always runnable: `pgrep -x claude` count is emitted for operator visibility only; the script never aborts because multiple Claude processes are running.
- Age-based retention: removes entries under `${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions/` and matching `/tmp` larch patterns when newest activity is older than the retention cutoff (`LARCH_CLEANUP_RETENTION_DAYS`, default 7). Invalid env values warn on stderr and fall back to 7.
- Clock failures are fatal: if `date +%s` does not yield a numeric epoch, cleanup exits non-zero and removes nothing.
- Activity scan: `newest_activity_mtime` compares the entry's own mtime with the newest mtime among descendants found by `find "$entry" -mindepth 1 -maxdepth 5`.
- Activity-scan failures fail closed per entry: if `find` cannot enumerate an entry's descendants, cleanup warns and skips deleting that entry.
- Rejects symlinked top-level session or `/tmp` pattern entries (`-L`); never `rm -rf` through a symlink.
- Reaps broken `current-design-env-*.sh` symlinks in the sessions parent (`-type l` and `! -e`).
- Never removes an entry it cannot prove exists (`[[ -e "$entry" || -L "$entry" ]]` guard).
- Uses bash 3.2-compatible `while IFS= read -r -d $'\0'` — not `mapfile`.

**Outputs** (stdout, KEY=value):
- `SESSION_COUNT=<N>` — number of `claude` processes detected (informational).
- `CACHE_REMOVED=<N>` — count of stale entries removed from the cache dir.
- `TMP_REMOVED=<N>` — count of stale `/tmp` entries removed.
- `SYMLINKS_REMOVED=<N>` — count of dangling `current-design-env-*.sh` symlinks removed.

**Edit-in-sync**: when adding a new `/tmp` pattern, update the `TMP_PATTERNS` array in `cleanup.sh`. Update `skills/cleanup/SKILL.md`, `docs/configuration-and-permissions.md` (`LARCH_CLEANUP_RETENTION_DAYS`), and `skills/cleanup/scripts/test-cleanup.sh` when changing retention, depth-5 activity scanning, or symlink reaping.
