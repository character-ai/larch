## Goal
Add a mechanical contract for plan-goals-test.md composition so pointer-only placeholders (e.g., "See plan.txt") are caught at write time rather than silently committed.

## Implementation Plan
## Goal
Add a mechanical contract for plan-goals-test.md composition so pointer-only placeholders (e.g., "See plan.txt") are caught at write time rather than silently committed.

## Implementation Plan

### Part A — Composer script `scripts/compose-plan-goals-test.sh`
- Accepts `--plan-file <path>` (required) and `--goal-text <text>` (optional, defaults to empty)
- Validates: plan file exists, is non-empty, and content >= 64 bytes; exits non-zero on failure
- Emits to stdout: `## Goal\n<goal text>\n\n## Implementation Plan\n<full plan body>\n\n## Test plan\n<extracted or fallback>`
- Test-plan extraction: scan plan body for a `## Test plan` or `# Test plan` heading; take all lines after it; if absent, emit "(no test plan section in plan-file)"
- Sibling doc `scripts/compose-plan-goals-test.md`

### Part B — Sanitizer in `scripts/lib-larch-log.sh`
Add `plan-goals` case to `larch_log_validate_batch_payload`:
```
plan-goals)
    if awk '/^## Implementation Plan$/,/^## /' "$file" \
        | sed '1d;/^## /d;/^$/d' \
        | head -c 64 \
        | grep -Eiq "^(see plan\.txt|see attached|see linked|tbd|todo)\.?$"; then
        larch_log_fail 2 "plan-goals sanitizer rejected: Implementation Plan body is a pointer-only placeholder"
    fi
    ;;
```

### Part C — Wire sanitizer in `scripts/larch-log-batches.sh`
Change `plan-goals-test .md replace none` → `plan-goals-test .md replace plan-goals`

### Part D — Update `scripts/test-larch-logs-batches.sh`
- Accept `plan-goals` in the sanitizer validation loop
- Add two payload tests: (a) "See plan.txt" body → exits non-zero; (b) real plan body → exits zero

### Part E — SKILL.md update (Step 1 "Larch-log batches" item 1)
Replace the current prompt-only prose with an invocation of `compose-plan-goals-test.sh`:
```
Run ${CLAUDE_PLUGIN_ROOT}/scripts/compose-plan-goals-test.sh --plan-file "$PLAN_FILE" \
  --goal-text "<one-sentence objective>" > "$IMPLEMENT_TMPDIR/plan-goals-test.md"
```
The script fails closed (non-zero) when plan body is absent/short/pointer-only. Write the output with `larch-log.sh write ... --batch plan-goals-test --input-file "$IMPLEMENT_TMPDIR/plan-goals-test.md"`.

### Part F — Test harness `scripts/test-compose-plan-goals-test.sh`
Tests:
1. Normal plan with test-plan section → correct output structure
2. Normal plan without test-plan section → fallback message
3. Plan body < 64 bytes → non-zero exit
4. "See plan.txt" (21 bytes) → non-zero exit
5. Empty plan file → non-zero exit
6. Missing plan file → non-zero exit
Sibling stub doc `scripts/test-compose-plan-goals-test.md`

## Test plan
- `scripts/test-compose-plan-goals-test.sh` (new harness, all 6 cases)
- `scripts/test-larch-logs-batches.sh` extended with plan-goals sanitizer tests
- `/relevant-checks` clean
