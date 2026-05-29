# `scripts/test-rebase-push-no-push-fetch-retry.sh` — contract

**Purpose**: offline regression test for `scripts/rebase-push.sh` `--no-push` transient `git fetch` retry.

## Coverage / Scope

- Transient fetch failure on the first attempt, then success on retry — script exits `0` with `SKIPPED_ALREADY_FRESH=true` when `HEAD` already contains the base ref.
- Persistent (exhausted) transient fetch failure — script exits `3` with `REBASE_ERROR=git fetch origin main failed (network/auth issue)`.

## Invocation

```bash
make test-rebase-push-no-push-fetch-retry
```

Registered in `Makefile` (`test-harnesses-16` shard) and excluded from orphan-file checks in `agent-lint.toml`.

## Invariants

- Default-mode fetch tolerance (`|| true`) is not exercised here.
- Retry backoff uses a no-op `sleep-seconds.sh` via `SLEEP_SCRIPT_DIR`.

## Edit-in-sync rules

Update this harness when changing:

- `scripts/rebase-push.sh` `--no-push` fetch or transient-retry behavior.
- `scripts/rebase-push.md` contract for `--no-push` fetch failures.
