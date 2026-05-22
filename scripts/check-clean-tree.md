# check-clean-tree.sh contract

## Purpose

`scripts/check-clean-tree.sh` is the shared working-tree cleanliness predicate for preflight gates. It centralizes the `git status --porcelain` probe used by `scripts/preflight.sh` and the pre-lock guard in `skills/fix-issue/scripts/find-lock-issue.sh`.

## Interface

```
check-clean-tree.sh [--fail-closed]
```

Default mode is fail-open: if `git status --porcelain` fails, the script emits `CLEAN=true` and exits 0.

With `--fail-closed`, probe failure emits `CLEAN=unknown`, emits `PROBE_ERROR=<single-line summary>`, and exits 1. `find-lock-issue.sh` uses this mode because it must not mutate GitHub issue state when local cleanliness cannot be determined.

## Output Contract

Clean tree:

```
CLEAN=true
```

Dirty tree:

```
CLEAN=false
DIRTY_OUT=<one-line git status summary>
```

Probe failure with `--fail-closed`:

```
CLEAN=unknown
PROBE_ERROR=<one-line summary>
```

The `DIRTY_OUT` and `PROBE_ERROR` values collapse newlines, carriage returns, and tabs to spaces, then cap the summary at 256 bytes. On probe failure, raw `git status` diagnostics are also echoed to stderr for operator debugging.

## Primary Callers

- `scripts/preflight.sh` calls `--fail-closed` (with `|| true` to preserve `set -e` compatibility); the awk-based CLEAN extraction then treats an empty result as "could not determine cleanliness" and exits 2.
- `skills/fix-issue/scripts/find-lock-issue.sh` calls `--fail-closed` immediately before issue-lock acquisition, so dirty trees abort before `GO` deletion, `IN PROGRESS` comments, or title renames.

## Test Harness

The dedicated harness is:

```
bash scripts/test-check-clean-tree.sh
```

## Makefile Wiring

`make test-check-clean-tree` runs the dedicated harness and is included in the `test-harnesses-N` shard partition.

## Related

`scripts/check-main-sync.sh` is the companion script for detecting committed-but-unpushed larch-log flush commits on local `main`. Both scripts are called on the same pre-lock and pre-run paths; `check-clean-tree.sh` covers uncommitted working-tree changes and `check-main-sync.sh` covers ahead commits.

## Edit-in-sync

When changing this helper's stdout contract, update both callers, `scripts/preflight.md`, `skills/fix-issue/scripts/find-lock-issue.md`, and `scripts/test-check-clean-tree.sh` in the same PR.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
