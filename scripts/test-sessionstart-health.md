# scripts/test-sessionstart-health.sh — contract

Regression harness for `scripts/sessionstart-health.sh` (the SessionStart preflight hook that probes `jq` and `git`). Wired into `make lint` via the `test-sessionstart` target. The full contract — including the always-exit-0 invariant required by SessionStart and the fixed-ASCII `additionalContext` literals — is owned by `scripts/sessionstart-health.md`.
