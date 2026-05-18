# `scripts/test-rebase-push-force-lease.sh` — contract

**Purpose**: offline regression test for `scripts/rebase-push.sh` force-push lease-race recovery.

## Coverage

The harness PATH-stubs `git` so `rebase-push.sh` can run without a real repository and simulates this sequence:

1. fetch/rebase succeeds,
2. the first `git push --force-with-lease` fails,
3. a branch refresh fetch shows `origin/<branch>` already matches local `HEAD`.

It asserts that `rebase-push.sh` exits 0, refreshes the branch tracking ref after the failed push, and does not sleep or attempt a second push once the refreshed remote state matches local `HEAD`.

## Invocation

```bash
bash scripts/test-rebase-push-force-lease.sh
```

## Edit-in-sync Rules

Update this harness with:

- `scripts/rebase-push.sh` when push-retry, lease-recovery, or branch-refresh behavior changes.
- `scripts/rebase-push.md` when the script-level force-push contract changes.
