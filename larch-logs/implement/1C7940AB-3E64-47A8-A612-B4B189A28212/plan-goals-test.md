## Goal
Serialize concurrent appends to append-execution-issue.sh with a portable mkdir-based mutex

## Implementation Plan
## Implementation Plan

### Goal
Add a portable mkdir-based mutex to `scripts/append-execution-issue.sh` to serialize concurrent appends and prevent entry loss when multiple callers race on the same LOG_FILE.

### Root Cause
The script uses an atomic mv-via-tmpfile pattern that prevents data corruption but not entry loss: two concurrent appenders can both read the same baseline LOG_FILE, produce independent awk-transformed tmp files, and the last mv wins — the other's entry is lost.

### Files to Modify
- `scripts/append-execution-issue.sh` — add mutex (~13 LOC)
- `scripts/append-execution-issue.md` — note concurrency safety

### Approach

After the parent directory creation and log-file initialization (lines 53–65), before entry_tmp creation (line 67):

1. Set `LOCK_DIR="${LOG_FILE}.lock.d"` — a sibling directory to LOG_FILE in the same parent.
2. Bounded retry loop: attempt `mkdir "$LOCK_DIR"` (atomic on POSIX); on failure sleep 0.05s and retry up to 100 times (5 seconds max). Exceeding the limit exits with `FAILED=true / ERROR=could not acquire lock`.
3. Modify the existing EXIT trap (currently `trap 'rm -f "$tmp" "$entry_tmp"' EXIT` at line 98) to also rmdir the lock: `trap 'rm -f "$tmp" "$entry_tmp"; rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT`.
4. On the success path, before `trap - EXIT` (line 149): add `rmdir "$LOCK_DIR" 2>/dev/null || true` to explicitly release the lock before clearing the trap.

### Lock Acquisition Detail

```bash
LOCK_DIR="${LOG_FILE}.lock.d"
_lock_retries=0
until mkdir "$LOCK_DIR" 2>/dev/null; do
    _lock_retries=$(( _lock_retries + 1 ))
    if [ "$_lock_retries" -ge 100 ]; then
        echo "FAILED=true"
        echo "ERROR=could not acquire lock: $LOCK_DIR"
        exit 2
    fi
    sleep 0.05
done
```

### Invariants
- Bash-3.2 portable (mkdir, sleep, arithmetic — no flock, no process substitution)
- POSIX: mkdir is atomic — only one concurrent caller gets the directory
- All existing failure exit paths (exits 2 before the trap is set) exit before lock acquisition and need no lock release
- The EXIT trap covers the failure path after lock acquisition
- The explicit rmdir before `trap - EXIT` covers the success path
- Stale lock from a crashed process: cleared naturally because lock dir is in the session tmpdir which is cleaned up by cleanup-tmpdir.sh

### Testing / Verification
- Run `/relevant-checks` after the change
- Manual verification: grep for APPENDED=true on a single invocation
- The issue specifically calls out dispatch-panel.sh background subshells as the affected caller; the fix removes the race without changing the script's interface or output

## Test plan
(no test plan section in plan-file)
