# test-plan-review-loop.sh

Offline regression harness for `plan-review-loop.sh`.

**Makefile**: `test-plan-review-loop`

## Coverage (smoke)

- `plan-review-loop.sh` parses argv and fails closed on missing required inputs.
- Script remains executable and syntactically valid (`bash -n`).

Expand with stubbed PATH scenarios per #2676 as follow-up.
