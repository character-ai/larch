# scripts/ci-status.sh — contract

`scripts/ci-status.sh` is the snapshot probe invoked by `scripts/ci-wait.sh`. It fetches a base ref, queries `gh pr checks --json` for the named PR, and counts commits behind that base. Defaults preserve `origin/main`; `/implement --forked` passes `--base-remote upstream --base-ref main` so staleness is measured against upstream main, not the fork's main.

It always exits 0. Status is communicated via three stdout lines in fixed order: `CI_STATUS=pass|fail|pending|merged|NO_CHECKS`, `BEHIND_COUNT=<N>`, `FAILED_RUN_ID=<id>` (empty when no failure). `NO_CHECKS` is emitted only when `--empty-checks-grace SECONDS` is non-zero and the checks array/text is still empty after the grace period; `ci-wait.sh` exits its loop with a bail action for that status.

Harness: `scripts/test-ci-status.sh`.
