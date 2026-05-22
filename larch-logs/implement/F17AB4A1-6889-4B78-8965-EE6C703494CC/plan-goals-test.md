## Goal
Add pre-run check for committed-but-unpushed larch-log flush commits; auto-reset if all are flush commits, block otherwise

## Implementation Plan

### Goal
Detect and auto-fix committed-but-unpushed larch-log flush commits on local main
before a run starts. Blocks runs if non-log commits are present on local main.

### Files to create
1. scripts/check-main-sync.sh — new check script
2. scripts/check-main-sync.md — contract doc
3. scripts/test-check-main-sync.sh — regression harness

### Files to modify
4. scripts/preflight.sh — call check-main-sync after git fetch origin main
5. scripts/preflight.md — document new check behavior
6. scripts/check-clean-tree.md — note related script
7. skills/fix-issue/scripts/find-lock-issue.sh — add pre-lock sync check
8. skills/fix-issue/scripts/find-lock-issue.md — document new check
9. Makefile — add test-check-main-sync target, wire to shard

### Design of check-main-sync.sh
- Checks current branch is main; if not, exits 0 with SYNC_STATUS=not-main
- Counts commits ahead of origin/main via git rev-list --count origin/main..HEAD
- If 0 ahead: SYNC_STATUS=ok, exit 0
- If all ahead commits match "chore(larch-logs): flush *" subjects AND all
  changed files are under larch-logs/: reset --hard origin/main, SYNC_STATUS=reset, exit 0
- If non-log commits present: SYNC_STATUS=blocked, ERROR=..., exit 1
- On git probe failure: SYNC_STATUS=probe-error, ERROR=..., exit 2

### Integration in preflight.sh
- After git fetch origin main (line 72), before git rebase origin/main
- Map exit 1 to PREFLIGHT=fail PREFLIGHT_ERROR=... exit 3
- Exit 2 (probe failure): fail-open (don't block run)

### Integration in find-lock-issue.sh
- Inside _emit_dirty_tree_pre_lock_abort, after the dirty-tree probe returns clean
- Map exit 1 to ELIGIBLE=false ERROR=... exit 2 (same pre-lock abort pattern)
- Same umbrella-context keys emitted when umbrella path


## Test plan
- test-check-main-sync.sh: sterile git repos; cases: in-sync, all-flush ahead,
  non-log ahead, not-on-main, probe-failure
- Verify preflight.sh change doesn't break test-preflight-args.sh
  (existing tests use repos without origin/main; check should be no-op)
