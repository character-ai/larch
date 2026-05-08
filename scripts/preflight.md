# preflight.sh contract

## Purpose

Run the pre-skill git sanity check used by `session-setup.sh`. In default mode it verifies that the caller is on `main`, the working tree is clean, and local `main` can fetch and rebase onto `origin/main`. `--skip-branch-check` skips only the on-main assertion and rebase. `--skip-clean-check` skips only the clean-tree assertion. All modes still fetch `origin/main`.

The clean-tree assertion delegates to `scripts/check-clean-tree.sh` in its default fail-open mode, preserving the prior `git status --porcelain 2>/dev/null` behavior where a failed cleanliness probe does not itself fail preflight. `skills/fix-issue/scripts/find-lock-issue.sh` uses the same helper with `--fail-closed` before acquiring an issue lock; both callers share the dirty-tree message family, but differ deliberately on probe-failure handling.

## Interface

```
preflight.sh [--skip-branch-check] [--skip-clean-check]
```

## Output contract

Success emits:

```
PREFLIGHT=ok
```

Failure for the documented runtime checks (not-on-main, dirty working tree, fetch failure, rebase failure) emits:

```
PREFLIGHT=fail
PREFLIGHT_ERROR=<human-readable reason>
```

`session-setup.sh` captures and re-emits these lines verbatim on preflight failure.

Argument validation (unknown flag) is the exception: it writes `Unknown option: <arg>` to stderr only and exits 3 without emitting the `PREFLIGHT_*` shape. Callers passing only documented flags will not encounter this path.

## Exit codes

| Exit | Meaning |
|------|---------|
| 0 | All requested checks passed. |
| 1 | Current branch is not `main` and `--skip-branch-check` was not passed. |
| 2 | Working tree is not clean and `--skip-clean-check` was not passed. |
| 3 | Argument validation failed, fetch failed, or rebase failed. |

## Flag Matrix

| Flags | Branch check | Clean-tree check | Fetch | Rebase |
|-------|--------------|------------------|-------|--------|
| none | yes | yes | yes | yes |
| `--skip-branch-check` | no | yes | yes | no |
| `--skip-clean-check` | yes | no | yes | no |
| both | no | no | yes | no |

After the clean-tree check passes, or when it is explicitly skipped, `preflight.sh` removes `$(git rev-parse --git-path larch-stalled-run.txt)` best-effort. That clears the stalled-run sentinel once the next task has successfully reached a clean or intentionally-clean-skipped launch point.

## Rebase failure shape

When both the branch check and clean-tree check are enabled, `git rebase origin/main` runs only after the clean-tree check has passed. If the rebase fails, `preflight.sh` immediately runs `git rebase --abort 2>/dev/null || true` before emitting `PREFLIGHT=fail` and exiting 3. Callers do not resolve conflicts during preflight; the abort restores the clean preflight starting point whenever Git can abort the failed rebase.

`--skip-branch-check` and `--skip-clean-check` modes do not run a rebase, so this abort behavior applies only when both checks remain enabled.

## Test harness

The dedicated harness is:

```
bash scripts/test-preflight-args.sh
```

## Makefile wiring

`make test-preflight-args` runs the dedicated harness and is included in `the test-harnesses-N shard partition`.

## Edit-in-sync

When changing `scripts/preflight.sh`:

- Update this file for any output contract, exit code, or git-state side effect change.
- Update `scripts/check-clean-tree.md` if the clean-tree helper contract changes.
- Update `skills/fix-issue/scripts/find-lock-issue.md` if dirty-tree messaging equivalence changes.
- Verify `scripts/session-setup.sh` still captures and re-emits `PREFLIGHT_*` output correctly.
- Verify `/implement` and `/design` setup prose still matches the default versus `--skip-branch-check` behavior.
