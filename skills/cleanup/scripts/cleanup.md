# cleanup.sh — Contract

**Purpose**: Remove leftover larch session temp directories. Called by `/cleanup` Step 1.

**Primary callers**: `skills/cleanup/SKILL.md` Step 1.

**Invariants**:
- Aborts with exit 1 when `pgrep -x claude` reports more than one running `claude` process.
- Removes all entries under `${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions/` when the directory exists.
- Removes `/tmp` entries matching the larch pattern list (see script body).
- Never removes an entry it cannot prove exists (`[[ -e "$entry" || -L "$entry" ]]` guard).

**Outputs** (stdout, KEY=value):
- `SESSION_COUNT=<N>` — number of `claude` processes detected.
- `CACHE_REMOVED=<N>` — count of entries removed from the cache dir.
- `TMP_REMOVED=<N>` — count of `/tmp` entries removed.

**Edit-in-sync**: when adding a new `/tmp` pattern, update the `TMP_PATTERNS` array in `cleanup.sh`. No other files require synchronization for pattern changes.
