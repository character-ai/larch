# test-design-step-validator-autofix.sh

## Purpose

Offline regression harness for `design-step-validator-autofix.sh`.

## Primary callers

- `Makefile` target `test-design-step-validator-autofix`

## Invariants

- Exercises escalation, operator-cancel, ok auto-fix audit, and false-ok nonzero helper behavior.
- Uses local stubs for validator and dispatch paths.

## Harness

Run via `make test-design-step-validator-autofix`.
