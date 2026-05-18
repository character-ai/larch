# `scripts/test-git-push.sh` — contract

**Purpose**: offline regression test for `scripts/git-push.sh` retry exit propagation.

## Coverage

The harness creates a temporary git repository on a named branch, PATH-stubs `git push` to fail three times with a stable non-zero exit code, stubs `sleep` to keep the test fast, and asserts that `git-push.sh`:

1. emits `BRANCH=<name>` before attempting the push loop,
2. retries exactly 3 times, and
3. exits with the underlying `git push` failure code instead of incorrectly reporting success after exhausting retries.

## Invocation

```bash
bash scripts/test-git-push.sh
```

## Edit-in-sync Rules

Update this harness with:

- `scripts/git-push.sh` when retry count, stdout contract, or exit propagation changes.
- `scripts/git-push.md` when the script-level push contract changes.
