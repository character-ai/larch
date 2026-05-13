# test-ci-wait.sh

Offline regression harness for `scripts/ci-wait.sh`. Covers the poll-count budget, suspend-resilience (per-iteration delta guard), happy path, and genuine-timeout cases.

## Primary contract

See `scripts/ci-wait.md` for the full `ci-wait.sh` interface and invariants.

## Makefile target

`make test-ci-wait`
