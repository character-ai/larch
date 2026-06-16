# test-design-step1d5.sh

## Purpose

Offline regression harness for `design-step1d5.sh --mode collect`.

## Primary callers

- `Makefile` target `test-design-step1d5`

## Invariants

- Stubs `python3 python/cli.py` calls so no external reviewer collector runs.
- Verifies collect argv, per-slot stdout relay, launch-failure run-log idempotency, and dirty-tree recovery env output.

## Harness

Run via `make test-design-step1d5`.
