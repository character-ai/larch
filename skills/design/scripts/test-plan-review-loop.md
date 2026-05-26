# test-plan-review-loop.sh

Offline regression harness for `plan-review-loop.sh`.

**Makefile**: `test-plan-review-loop`

## Coverage (smoke)

- `plan-review-loop.sh` parses argv and fails closed on missing required inputs.
- Script remains executable and syntactically valid (`bash -n`).

Stub cases cover zero findings, a real single-finding tally, panel-failed
header-only artifacts, a tally-failure degraded `voting-tally.md`, and
canonical-slot preservation when the middle voter fails.
