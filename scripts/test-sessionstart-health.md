# scripts/test-sessionstart-health.sh — contract

Regression harness for `scripts/sessionstart-health.sh` (the SessionStart
preflight hook that probes `jq`, `git`, leftover git state, and pending
/implement boundary state). Wired into
`make lint` via the `test-sessionstart` target. The full contract, including
the always-exit-0 invariant, jq-based JSON encoding rule, and fixed-literal
jq-missing fallback, is owned by `scripts/sessionstart-health.md`.

Boundary coverage includes sparse-cone drift advisories (drift, match, no clone,
missing library/function, cwd independence, empty `HOME`, non-git marketplace,
legacy `larch-logs/`, and empty compare inputs), `.run-cleaned-up` suppression, post-/review
summary detection plus `.review-boundary-passed` suppression, and the Phase 1
retirement of post-/release `.release-armed` advisories. It also asserts the
combined edge case where pending review state remains visible while retired
release sentinels stay silent.
