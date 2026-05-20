## Goal
Fix scout 100% parse-failed: strengthen prompt, add fence-stripping, and add SCOUT_FAIL_REASON telemetry

## Implementation Plan

Goal: Fix scout 100% parse-failed by (A) strengthening the prompt and adding fence-stripping preprocessing, (B) adding SCOUT_FAIL_REASON telemetry, and (C) emitting execution-issues warning on parse-fail.

### Files to modify

1. **scripts/scout-dynamic-archetypes.sh** — prompt strengthening + fence stripping + SCOUT_FAIL_REASON
2. **skills/review/scripts/dispatch-panel.sh** — parse/emit SCOUT_FAIL_REASON, add execution-issues warning
3. **skills/review/scripts/review-core.sh** — parse scout_fail_reason from dispatch, write to status.env
4. **scripts/test-scout-dynamic-archetypes.sh** — add regression tests for fence-wrapped JSON and SCOUT_FAIL_REASON
5. **scripts/scout-dynamic-archetypes.md** — update stdout contract docs
6. **skills/review/scripts/dispatch-panel.md** — update stdout keys + mention execution-issues warning
7. **skills/review/scripts/review-core.md** — add SCOUT_FAIL_REASON to emitted keys

### Part B: Prompt strengthening + fence stripping

**scripts/scout-dynamic-archetypes.sh** changes:

1. After the format instruction line (~line 192), add two prompt lines:
   - `printf 'Output ONLY the raw JSON object — no markdown code fences, no backticks, no prose.\n'`
   - `printf 'The "rationale" field must be a single line with no embedded newlines.\n'`

2. After the `launch_rc -ne 0` check block (~line 247), add JSON fence stripping:
   - If `jq -e '.' "$raw_output"` fails (not valid JSON), try awk to extract JSON from code fences
   - `awk '/^```/{if(!in_block){in_block=1;next}else{in_block=0;next}} in_block{print}' "$raw_output"`
   - If extracted content is non-empty and valid JSON, replace raw_output with it

### Part C: SCOUT_FAIL_REASON

**scripts/scout-dynamic-archetypes.sh** changes:
3. At first jq gate failure (~line 249-256): add `emit_kv SCOUT_FAIL_REASON json_parse`
4. At count overflow check (~line 258-267): add `emit_kv SCOUT_FAIL_REASON archetype_count_overflow`
5. At complex jq failure (~line 329-338): add `emit_kv SCOUT_FAIL_REASON validation_jq_error`

**skills/review/scripts/dispatch-panel.sh** changes:
6. Add `SCOUT_FAIL_REASON=""` variable after `SCOUT_STATUS="na"` (~line 36)
7. Parse `SCOUT_FAIL_REASON` in the scout output case block (~line 280)
8. Emit `SCOUT_FAIL_REASON` in dispatch stdout when non-empty (~line 363)
9. After main dynamic archetypes `fi` block (~line 319), when SCOUT_STATUS=parse-failed, call
   `append-execution-issue.sh --category Warnings` with path resolved via
   LARCH_EXECUTION_ISSUES_LOG → SESSION_ENV_PATH/dirname → IMPLEMENT_TMPDIR → REVIEW_TMPDIR

**skills/review/scripts/review-core.sh** changes:
10. Parse `scout_fail_reason` from dispatch output (~line 302)
11. Write `SCOUT_FAIL_REASON` to status.env at lines 310-314 when non-empty

### Regression tests (scripts/test-scout-dynamic-archetypes.sh)

12. Add test for fence-wrapped JSON: stub outputs ```json\n{valid json}\n```, assert SCOUT_STATUS=ok
13. Add test for fence-with-prose: stub outputs prose + ```json block, assert SCOUT_STATUS=ok
14. Assert SCOUT_FAIL_REASON=json_parse in the malformed test
15. Assert SCOUT_FAIL_REASON=archetype_count_overflow in the too-many test


## Test plan

- Run `make test-scout-dynamic-archetypes` to verify regression tests pass
- Run `make lint` to verify no shell linting issues
- Run `make test-dispatch-panel` to verify dispatch panel tests pass
