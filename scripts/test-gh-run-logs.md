# scripts/test-gh-run-logs.sh — contract

Regression harness for `scripts/gh-run-logs.sh`. Stubs the `gh` binary to return synthetic responses and verifies the script's exit-code contract, including the exit-2 in-progress sentinel added by issue #2432.

See `scripts/gh-run-logs.md` for the primary contract.
