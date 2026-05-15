# detect-wholesale-rejection.sh Contract

`skills/review/scripts/detect-wholesale-rejection.sh` emits whether the review loop should terminate after every finding in a round was rejected.

Stdout is `TERMINATE_EARLY=true|false`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-detect-wholesale-rejection.sh`, wired through `make test-detect-wholesale-rejection`.
