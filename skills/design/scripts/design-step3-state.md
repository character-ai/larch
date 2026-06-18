# design-step3-state.sh

## Purpose

Legacy-compatible Step 3 sentinel mutation helper for `/design`.

## Primary callers

- `python3 python/cli.py plan-review step3-state`, through the embedded legacy asset materialized by `python/plan_review.py`.
- Runtime wrappers that call the CLI surface, not this file directly.

## Invariants

- Keep this file byte-identical to the `_LEGACY_ASSETS` entry in `python/plan_review.py`.
- `--direct-review-entry` and `--auto-continuation-entry` clear stale Step 3 terminal recovery sentinels before launching another Step 3 review pass.
- `step-3` and `step-3.5` remain the pause and Gate B milestones. They are not hook-release sentinels.

## Harness

Covered by `python/test_plan_review.py` via the live/embedded parity test and `plan-review step3-state` CLI tests.
