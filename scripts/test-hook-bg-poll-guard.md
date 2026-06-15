# test-hook-bg-poll-guard.sh

## Purpose

Offline regression harness for `scripts/hook-bg-poll-guard.sh`.

## Primary callers

- `Makefile` target `test-hook-bg-poll-guard`.

## Invariants

- Exercises the shipped `hooks/hooks.json` registration and the guard's allow, deny, fail-open, stale-marker, wrapper-routed, Step 3 recovery-waiter, and telemetry paths.
- Covers positive `.completed/step-3` recovery waiters, the braced `${DESIGN_TMPDIR}` form, appended-probe denial, and continued `.step3-review-result.env` waiter denial.
- Uses a temporary marker path supplied through `LARCH_BG_POLL_GUARD_MARKER`; it does not depend on a real Claude Code session.

## Harness

Run with `bash scripts/test-hook-bg-poll-guard.sh`.
