# scripts/test-sessionstart-health.sh — contract

Regression harness for `scripts/sessionstart-health.sh` (the SessionStart
preflight hook that probes `jq`, `git`, leftover git state, and pending
/implement boundary state). Wired into
`make lint` via the `test-sessionstart` target. The full contract, including
the always-exit-0 invariant, jq-based JSON encoding rule, and fixed-literal
jq-missing fallback, is owned by `scripts/sessionstart-health.md`.

Boundary coverage includes post-/design manifest detection plus
`.boundary-gate-passed` and `.run-cleaned-up` suppression, post-/review
summary detection plus `.review-boundary-passed` suppression, and
post-/bump-version `.bump-version-armed` detection plus `postbump-state.sh`
suppression.
