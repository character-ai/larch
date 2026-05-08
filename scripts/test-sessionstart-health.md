# scripts/test-sessionstart-health.sh — contract

Regression harness for `scripts/sessionstart-health.sh` (the SessionStart
preflight hook that probes `jq`, `git`, and leftover git state). Wired into
`make lint` via the `test-sessionstart` target. The full contract, including
the always-exit-0 invariant, jq-based JSON encoding rule, and fixed-literal
jq-missing fallback, is owned by `scripts/sessionstart-health.md`.
