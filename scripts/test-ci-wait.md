# test-ci-wait.sh

Offline regression harness for `scripts/ci-wait.sh`. Covers the poll-count budget, suspend-resilience (per-iteration delta guard), happy path, and genuine-timeout cases.

## Primary contract

See `scripts/ci-wait.md` for the full `ci-wait.sh` interface and invariants.

## Makefile target

`make test-ci-wait`

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so failures cannot append to a
parent `/implement` run's log.
