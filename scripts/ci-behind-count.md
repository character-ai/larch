# scripts/ci-behind-count.sh — contract

Counts how many commits `HEAD` is behind `${BASE_REMOTE}/${BASE_REF}` using `git rev-list "HEAD..$BASE_TARGET" --count`. Shared by `scripts/ci-status.sh` (with `--no-fetch` after its own fetch) and the CI-fix push path in `scripts/ship-pr.sh`.

## Interface

```text
ci-behind-count.sh [--base-remote NAME] [--base-ref BRANCH] [--no-fetch]
```

Defaults: `origin` / `main`. Emits `BEHIND_COUNT=<n>` on the `lib-quiet.sh` contract stream and always exits `0`.

## Fail-open

When `git fetch` fails (unless `--no-fetch`), or when `git rev-list` fails or returns a non-integer, the script emits `BEHIND_COUNT=0` and a stderr diagnostic. Callers must not treat a count error as a hard push blocker.

Harness: `scripts/test-ci-behind-count.sh`.
