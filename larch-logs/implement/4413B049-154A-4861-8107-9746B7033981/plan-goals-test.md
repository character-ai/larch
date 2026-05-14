## Goal
Add a `json-lines` sanitizer to the larch-log batch system and fix SIMPLE-path tally composition to produce proper JSON records.

## Implementation Plan

### Fix A — json-lines sanitizer
1. `scripts/lib-larch-log.sh`: add `json-lines` case to `larch_log_validate_batch_payload`
2. `scripts/larch-log-batches.sh`: switch `plan-review-tally`, `code-review-tally`, `review-findings-full` to `json-lines` sanitizer
3. `scripts/test-larch-logs-batches.sh`: update enum + add functional tests

### Fix B — composer
4. New `scripts/compose-tally-record.sh` wrapping body in canonical JSON envelope
5. `skills/implement/SKILL.md`: update 3 SIMPLE-path tally composition sites
6. `scripts/larch-log-batches.md`: add schema docs

## Test plan
- `make lint` clean (runs test-larch-logs-batches.sh + agent-lint)
- Functional tests for json-lines validator (valid JSON passes, invalid text fails, empty file passes)
- Verify SKILL.md sites produce proper JSON
