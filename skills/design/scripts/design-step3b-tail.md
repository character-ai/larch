# design-step3b-tail.sh

## Purpose

Adapter-backed `/design` Step 4 rejected-findings and Gate C preview tail.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Resolves a supplied session env through the trusted bgjob resolver before pause handling or tmpdir use. It never sources the file.
- Delegates lifecycle decisions to `bgjob adapt` with step `design-step4-tail`, explicit tmpdir, 900-second budget, session path, and optional owner PID.
- Accepts child mode only as the terminal `--bgjob-child --merge-result-env <path>` suffix.
- Ordinary duplicate calls reattach a valid completed result. The wrapper does not inspect registry liveness or delete lifecycle artifacts.
- Keeps FINALIZE, rejected-finding rendering, Gate C, preview generation, and completion markers in child mode.
- Atomically publishes `STEP4_STATUS`, `SKIP_APPROVE_REQUESTED_GATEC`, rejected-body paths, preview paths, and an optional dialectic digest to the adapter merge env.
- A pause race runs pause-save, publishes `STEP4_STATUS=pause-save`, and exits zero. Publication failure exits non-zero.

## Harness

Covered by `make test-design-step3b-tail` and `make test-design-structure`.
