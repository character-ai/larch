# scripts/ci-status.sh — contract

`scripts/ci-status.sh` is the snapshot probe invoked by `scripts/ci-wait.sh`. It fetches a base ref, queries `gh pr checks --json` for the named PR, and counts commits behind that base via `scripts/ci-behind-count.sh --no-fetch` (the fetch happens once in `ci-status.sh` before the helper runs). Defaults preserve `origin/main`; `/implement --forked` passes `--base-remote upstream --base-ref main` so staleness is measured against upstream main, not the fork's main.

It always exits 0. Status is communicated via four stdout lines in fixed order: `CI_STATUS=pass|fail|pending|merged|NO_CHECKS`, `BEHIND_COUNT=<N>`, `FAILED_RUN_ID=<id>` (empty when no failure), `CONFLICTED=<true|false>`. `mergeStateStatus` is read from the same early `gh pr view --json state,mergeStateStatus` call used for the merged short-circuit (no extra API round-trip). `CONFLICTED=true` when `mergeStateStatus` is `DIRTY`, `UNKNOWN`, or empty; `false` for `CLEAN`, `BEHIND`, `BLOCKED`, `UNSTABLE`, and `HAS_HOOKS`. `NO_CHECKS` is emitted only when `--empty-checks-grace SECONDS` is non-zero and the checks array/text is still empty after the grace period; `ci-wait.sh` exits its loop with a bail action for that status.

Harness: `scripts/test-ci-status.sh`.
