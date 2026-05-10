# cleanup.sh — Contract

**Purpose**: Remove leftover larch session temp directories. Called by `/cleanup` Step 1.

**Primary callers**: `skills/cleanup/SKILL.md` Step 1.

**Invariants**:
- Aborts with exit 1 when `pgrep -x claude` reports more than one running `claude` process.
- Skips any `~/.cache/larch/sessions/<dir>` that contains a `.larch-keepalive` file (active session sentinel).
- Removes all non-keepalive entries under `${XDG_CACHE_HOME:-${HOME}/.cache}/larch/sessions/`.
- Removes `/tmp` entries matching the larch pattern list (see `TMP_PATTERNS` in script body).
- Never removes an entry it cannot prove exists (`[[ -e "$entry" || -L "$entry" ]]` guard).
- Uses bash 3.2-compatible `while IFS= read -r -d $'\0'` — not `mapfile`.

**Outputs** (stdout, KEY=value):
- `SESSION_COUNT=<N>` — number of `claude` processes detected.
- `CACHE_REMOVED=<N>` — count of non-keepalive entries removed from the cache dir.
- `TMP_REMOVED=<N>` — count of `/tmp` entries removed.

**Edit-in-sync**: when adding a new `/tmp` pattern, update the `TMP_PATTERNS` array in `cleanup.sh`. No other files require synchronization for pattern changes.
