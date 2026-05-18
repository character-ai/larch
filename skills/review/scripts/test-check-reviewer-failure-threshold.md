# test-check-reviewer-failure-threshold.sh

Regression harness for `skills/review/scripts/check-reviewer-failure-threshold.sh`.

## Coverage

- HARD (12-slot) panel: all OK, exactly half fail (6/12 → still OK), just-over-half fail (7/12 → fail), all fail (12/12 → fail).
- SIMPLE (7-slot) panel: under threshold (3/7), just-over (4/7).
- `STATUS=cap_hit` counted as success (deliberate slot-skip, not failure).
- `--launched-slots` accounting: never-launched slots count as failures (vendor unhealthy).
- Both-down case: zero records, zero launched → all 12 counted as failures.
- `STATUS=NOT_SUBSTANTIVE` counted as both `FAILED_SLOTS` and `NOT_SUBSTANTIVE_SLOTS`; threshold still triggers when majority are NOT_SUBSTANTIVE.

## Invocation

```bash
skills/review/scripts/test-check-reviewer-failure-threshold.sh
```

Exit 0 → pass, exit 1 → at least one assertion failed.
