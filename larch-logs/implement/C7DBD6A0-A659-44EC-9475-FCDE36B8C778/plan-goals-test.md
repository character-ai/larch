## Goal
Fix real sleeps in test-ci-wait.sh and snapshot grep performance in lib-gemini-launcher-review.sh

## Implementation Plan
## Implementation Plan

### Fix 1: scripts/test-ci-wait.sh — Cases 2 and 3 use real sleep 10

**Root cause**: Cases 2 (pending_then_pass) and 3 (suspend_sim) invoke run_subject
which runs ci-wait.sh, which has `sleep 10` in its polling loop. Case 2 loops 3x
for 30s; Case 3 loops 1x for 10s. Case 4 already uses a fake-sleep stub.

**Change**: In Case 2 (around line 116), add the same fake-sleep stub that Case 4
uses (fake-sleep.sh no-op + symlink as `sleep`). In Case 3 (around line 167), add
the same fake-sleep stub; the existing fake-date stub already simulates 70s elapsed,
and a no-op sleep still allows the suspend detection to fire correctly because the
date stub returns base+70 regardless of actual elapsed time.

Files: scripts/test-ci-wait.sh
Verification: `make test-ci-wait` should complete in ~3s instead of ~43s.

### Fix 2: scripts/lib-gemini-launcher-review.sh — capture_snapshot calls grep per file

**Root cause**: capture_snapshot iterates 1673 tracked files and calls
snapshot_status_file_mentions_path (which spawns grep) for each one. On a clean
repo with a small status file, this still takes ~5.8s per call × 2 calls × ~12
normal gemini invocations = ~140s total, dominating the 3m27s harness 8 runtime.

**Change**: In capture_snapshot, after `git status --porcelain > "$status_file"`,
pre-build a newline-delimited dirty-path set using one awk invocation. In the
tracked-files loop, replace the call to tracked_snapshot_hash (which calls grep)
with inline bash pattern matching against the pre-built set. For an empty/clean
status file, _dirty_set="" so the check is O(1) bash string eval. For a small dirty
set, it's O(|_dirty_set|) per file — much faster than 1673 subprocess spawns.

Also replace the snapshot_pre_status_mentions_path call in the backup-path check
with the same pre-built set check.

Keep tracked_snapshot_hash and snapshot_status_file_mentions_path intact.

Also update sibling .md files if they describe the changed behavior.

Files: scripts/lib-gemini-launcher-review.sh, scripts/lib-gemini-launcher-review.md
Verification: `make test-launch-review` should complete in ~65s instead of ~207s.

## Test plan
(no test plan section in plan-file)
