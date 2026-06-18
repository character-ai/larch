## Decision 1: Findings parity
- **Question**: Must the faster job flag exactly the same duplicates as today, or is an equivalent (not bit-identical) result acceptable if it is faster?
- **Resolution**: Equivalent is acceptable. A different engine or threshold is fine as long as it still catches genuine copy-paste; the exact flagged set may shift slightly. Hard constraint: the check must NOT be silently weakened — it must still fail CI when a real duplicate cluster (>= threshold lines) exists.
- **Source**: user

## Decision 2: Speed target
- **Question**: What is the bar for "fast enough"?
- **Resolution**: Target ~60-90s wall-clock for the CI `python-lint-duplicate-code` job, down from ~3 min. Verified in CI (the relevant runner is GitHub-hosted ubuntu-latest, slower than a local Apple-Silicon dev box where the current run is ~48s).
- **Source**: user

## Decision 3: Allowed changes (conservatism)
- **Question**: How conservative should the change be — pylint-only with identical coverage/threshold, or open to bigger changes?
- **Resolution**: Open to bigger changes if faster. A different duplicate-detection engine, a trimmed file set, or a different threshold are all acceptable if they cut time and keep the check valuable.
- **Source**: user

## Hard constraints carried into the plan
- The check must remain CORRECT for cross-file duplicates: any parallelization must not reintroduce the pylint `-j>1` slicing bug (each worker seeing only a file slice, missing cross-shard duplicates). This is the original reason the job is single-process (issue #4480).
- The CI gate must still FAIL the job when duplicates at/above the effective threshold are present (preserve exit-code-based gating).
- The local `make py-lint-duplicate-code` target must keep working for developers.
- Keep a single stable required status check for branch protection (use the repo's existing aggregate-gate pattern only if the job is split into a matrix).
