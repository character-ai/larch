# preflight.sh contract

## Purpose

Run the pre-skill git sanity check used by `session-setup.sh`. In default mode it verifies that the caller is on `main`, the working tree is clean, and local `main` can fetch and rebase onto `origin/main`. With `--skip-branch-check`, it skips the branch and clean-tree assertions and only refreshes `origin/main`.

## Interface

```
preflight.sh [--skip-branch-check]
```

## Output contract

Success emits:

```
PREFLIGHT=ok
```

Failure emits:

```
PREFLIGHT=fail
PREFLIGHT_ERROR=<human-readable reason>
```

`session-setup.sh` captures and re-emits these lines verbatim on preflight failure.

## Exit codes

| Exit | Meaning |
|------|---------|
| 0 | All requested checks passed. |
| 1 | Default mode only: current branch is not `main`. |
| 2 | Default mode only: working tree is not clean. |
| 3 | Argument validation failed, fetch failed, or default-mode rebase failed. |

## Rebase failure shape

In default mode, `git rebase origin/main` runs only after the working tree has been verified clean. If the rebase fails, `preflight.sh` immediately runs `git rebase --abort 2>/dev/null || true` before emitting `PREFLIGHT=fail` and exiting 3. Callers do not resolve conflicts during preflight; the abort restores the clean preflight starting point whenever Git can abort the failed rebase.

`--skip-branch-check` mode does not run a rebase, so this abort behavior is default-mode only.

## Test harness

No dedicated harness exists today. Syntax is covered by running:

```
bash -n scripts/preflight.sh
```

## Makefile wiring

No dedicated Makefile target exists today.

## Edit-in-sync

When changing `scripts/preflight.sh`:

- Update this file for any output contract, exit code, or git-state side effect change.
- Verify `scripts/session-setup.sh` still captures and re-emits `PREFLIGHT_*` output correctly.
- Verify `/implement` and `/design` setup prose still matches the default versus `--skip-branch-check` behavior.
