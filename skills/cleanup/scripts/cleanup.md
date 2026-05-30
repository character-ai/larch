# cleanup.sh — Contract

**Purpose**: Remove stale larch session temp directories by age and reap dangling `/design` session-env symlinks. Called by `/cleanup` Step 1.

**Primary callers**: `skills/cleanup/SKILL.md` Step 1.

**Invariants**:
- Always runnable: `pgrep -x claude` count is emitted for operator visibility only; the script never aborts because multiple Claude processes are running.
- Age-based retention: removes entries under `${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions/` and matching `/tmp` larch patterns when the entry's own (top-level) mtime is older than the retention cutoff via `find -mtime` (`LARCH_CLEANUP_RETENTION_DAYS`, default 7). Invalid env values warn on stderr and fall back to 7.
- Top-level enumeration: cache and `/tmp` passes use `find -mindepth 1 -maxdepth 1 ! -type l -mtime +N` (never delete through a symlink).
- Reaps broken `current-design-env-*.sh` symlinks in the sessions parent (`-type l` and `! -e`).
- Age-pass `find` enumeration errors are swallowed (`2>/dev/null` on `find`, `|| true` on the read loop); cleanup exits 0 and deletions may no-op with counts 0 rather than aborting.
- Uses bash 3.2-compatible `while IFS= read -r -d $'\0'` — not `mapfile`.

**Outputs** (stdout, KEY=value):
- `SESSION_COUNT=<N>` — number of `claude` processes detected (informational).
- `CACHE_REMOVED=<N>` — count of stale entries removed from the cache dir.
- `TMP_REMOVED=<N>` — count of stale `/tmp` entries removed.
- `SYMLINKS_REMOVED=<N>` — count of dangling `current-design-env-*.sh` symlinks removed.

**Edit-in-sync**: when adding a new `/tmp` pattern, update the `TMP_PATTERNS` array in `cleanup.sh`. Update `skills/cleanup/SKILL.md`, `docs/configuration-and-permissions.md` (`LARCH_CLEANUP_RETENTION_DAYS`), `SECURITY.md` (cleanup retention / enumeration trust boundary), and `skills/cleanup/scripts/test-cleanup.sh` when changing retention, top-level mtime age checks, or symlink reaping.
