## Goal
Change execution-issues/review-findings/oos-issues batch sanitizers from none to json-lines

## Implementation Plan

### Objective
Change sanitizer for `execution-issues`, `review-findings`, and `oos-issues` NDJSON batches from `none` to `json-lines` so that malformed (non-JSON) records are rejected at write time rather than silently accepted.

### Files to modify

1. **`scripts/larch-log-batches.sh`** — change three sanitizer columns:
   - `review-findings .ndjson append none` → `review-findings .ndjson append json-lines`
   - `oos-issues .ndjson append none` → `oos-issues .ndjson append json-lines`
   - `execution-issues .ndjson append none` → `execution-issues .ndjson append json-lines`

2. **`scripts/larch-log-batches.md`** — add a paragraph documenting the `json-lines` contract for these three batches.

3. **`scripts/test-larch-log.sh`** — add regression assertions that appending raw markdown to each of the three batches exits non-zero with `json-lines sanitizer rejected`.

4. **`scripts/test-larch-log.md`** — update coverage description to mention the new json-lines rejection tests.

### Call site audit (execution-issues)
- `scripts/implement-finalize.sh` safety-net: Uses `jq -c -Rs` to compose NDJSON records. ✅ Valid JSON.
- Orchestrator Step 11 direct append: Composes NDJSON inline with `jq`. ✅ Valid JSON.

### Call site audit (review-findings)
- `skills/review/scripts/log-phase.sh`: Passes caller-supplied payload file. Caller (prompt-level orchestrator) must supply NDJSON. The `json-lines` sanitizer adds the guard that was missing.

### Call site audit (oos-issues)
- Prompt-level orchestrator Step 9a.1: An existing run log (`larch-logs/implement/6AF4992B-.../oos-issues.ndjson`) contains markdown — this confirms the bug. The fix makes the sanitizer reject such writes.

### Testing strategy (TDD)
- Run `/relevant-checks` after changes pass.
- The new test cases in `test-larch-log.sh` directly exercise the json-lines rejection path for all three batches.

## Test plan
(no test plan section in plan-file)
