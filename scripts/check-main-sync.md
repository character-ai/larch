# check-main-sync.sh contract

## Purpose

`scripts/check-main-sync.sh` detects committed-but-unpushed larch-log flush commits on local `main` before a run starts. It complements `scripts/check-clean-tree.sh` (which checks only for uncommitted working-tree changes) by also checking whether local `main` is ahead of `origin/main` with committed commits.

When all ahead commits are larch-log flush commits (subject matches `chore(larch-logs): flush *` and all touched files are under `larch-logs/`), the script auto-resets local `main` to `origin/main` so the run can proceed cleanly. When non-log commits are present, it emits `SYNC_STATUS=blocked` and exits 1, preventing the run until the operator reconciles.

On any branch other than `main` the check is a no-op (exits 0 with `SYNC_STATUS=not-main`).

## Interface

```
check-main-sync.sh
```

No flags. Callers are responsible for fetching `origin/main` before invoking this script when an up-to-date comparison is needed (e.g. `preflight.sh` fetches before calling this; `find-lock-issue.sh` calls this without fetching, relying on the locally-cached `origin/main` ref).

## Output Contract

In-sync:

```
SYNC_STATUS=ok
AHEAD_COUNT=0
```

Not on main (check skipped):

```
SYNC_STATUS=not-main
```

All ahead commits are flush commits (auto-reset applied):

```
SYNC_STATUS=reset
AHEAD_COUNT=<N>
```

Non-log commits present:

```
SYNC_STATUS=blocked
AHEAD_COUNT=<N>
ERROR=local main is <N> commit(s) ahead of origin/main with non-log changes; push or reconcile before re-running
```

Git probe failure:

```
SYNC_STATUS=probe-error
ERROR=<summary>
```

## Exit Codes

| Exit | Meaning |
|------|---------|
| 0 | Sync is ok, check was not applicable (not-main), or flush commits were auto-reset. Run may proceed. |
| 1 | Blocked: non-log commits on local main ahead of origin/main. Caller should abort. |
| 2 | Argument validation error or git probe failure. |

## Primary Callers

- `scripts/preflight.sh` calls this immediately after `git fetch origin main` and before `git rebase origin/main`. Fetching ensures the comparison uses the current upstream state. Exit 1 maps to `PREFLIGHT=fail` + exit 3.
- `skills/fix-issue/scripts/find-lock-issue.sh` calls this inside `_emit_dirty_tree_pre_lock_abort` after the working-tree cleanliness probe passes. No fetch is performed — the locally-cached `origin/main` ref is used. Exit 1 maps to `ELIGIBLE=false` + exit 2, aborting before any GitHub mutation.

## Relationship to local-cleanup.sh

The orphan-drop logic in `local-cleanup.sh` Step 3 is the post-merge counterpart of this check. Both use the same criteria (`chore(larch-logs): flush *` commit subjects + `larch-logs/`-only file paths) to identify safe-to-drop flush commits. `check-main-sync.sh` runs pre-fetch (on the `find-lock-issue.sh` path) or post-fetch (on the `preflight.sh` path), before a squash-merge can interfere with the diff.

## Test Harness

```
bash scripts/test-check-main-sync.sh
```

`make test-check-main-sync` runs the dedicated harness.

## Makefile Wiring

`make test-check-main-sync` runs the dedicated harness and is included in the `test-harnesses-N` shard partition.

## Edit-in-sync

When changing this script's stdout contract, update both callers (`scripts/preflight.sh`, `skills/fix-issue/scripts/find-lock-issue.sh`), their companion `.md` files, and `scripts/test-check-main-sync.sh` in the same PR.
