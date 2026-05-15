## Goal
Adopt JSON sentinel for no-findings in plan-review; detect and classify Cursor empty-response mode

## Implementation Plan

### Goal
Fix the no-findings sentinel protocol for plan-review and /review:
1. Adopt JSON sentinel `{"no_issues_found": true}` in prompts (A)
2. Update the validator to accept both old and new sentinel (B)
3. Detect Cursor empty .result and write CURSOR_EMPTY_RESPONSE marker (C)
4. Map CURSOR_EMPTY_RESPONSE to STATUS=CURSOR_EMPTY_RESPONSE in collector (D)
5. Update sibling .md contracts (E)
6. Update test harnesses (F)

### A. Prompt updates

**`skills/design/scripts/render-plan-review-prompt.sh`** line ~101:
Replace:
  `If NO issues found, output exactly NO_ISSUES_FOUND on a single line — do NOT include a TSV block. Do NOT modify files.`
With:
  `If no issues were identified, your entire response content MUST be exactly the single-line JSON literal {"no_issues_found": true} — no surrounding prose, no TSV records, no out-of-scope items, no trailing whitespace beyond a single newline. For Cursor's --output-format json invocation this becomes .result = "{\"no_issues_found\": true}" in Cursor's JSON envelope; the larch tooling extracts .result and JSON-parses it to detect the sentinel. For Codex (which writes plain stdout), the literal is captured verbatim. Do NOT modify files.`

**`scripts/render-reviewer-prompt.sh`** line ~252:
Replace `SENTINEL_REPLACEMENT=` value with:
  `If no findings at all, your entire response content MUST be exactly the single-line JSON literal {"no_issues_found": true} (no surrounding prose, no records). Cursor wraps this as .result = "{\"no_issues_found\": true}"; the larch tooling JSON-parses the extracted .result and detects the sentinel. Codex consumers see the raw literal.`
Also update the comment at lines ~249-250.

### B. Validator updates (`scripts/validate-research-output.sh`)

**In `STRUCTURED_REVIEWER_MODE` block** (after line ~318 NO_ISSUES_FOUND check):
Add JSON sentinel check:
```bash
if command -v jq >/dev/null 2>&1 \
   && jq -e 'type == "object" and .no_issues_found == true' <<<"$TRIMMED" >/dev/null 2>&1; then
    write_structured_output "$WRITE_STRUCTURED" ""
    exit 0
fi
```

**Before `VALIDATION_MODE` block** (around line ~354): Add CURSOR_EMPTY_RESPONSE check:
```bash
if [[ "$VALIDATION_MODE" == "true" ]]; then
    TRIMMED=$(trimmed_nonblank_content "$INPUT")
    if [[ "$TRIMMED" == "CURSOR_EMPTY_RESPONSE" ]]; then
        printf 'STATUS=CURSOR_EMPTY_RESPONSE\nFAILURE_REASON=Cursor returned a JSON envelope with empty .result field — likely transient backend issue. Fallback engaged.\n' >&2
        exit 5
    fi
    if [[ "$TRIMMED" == "NO_ISSUES_FOUND" ]]; then
        exit 0
    fi
    if command -v jq >/dev/null 2>&1 \
       && jq -e 'type == "object" and .no_issues_found == true' <<<"$TRIMMED" >/dev/null 2>&1; then
        exit 0
    fi
fi
```

Note: exit code 5 is unused in the non-structured path (exit 2=thin, 3=no marker, 4=file missing). Exit 5 in STRUCTURED_REVIEWER_MODE is a separate code path that exits early; the two modes can't be in flight simultaneously.

### C. Launcher update (`scripts/launch-review.sh`)

After the extraction block (after line ~994, inside the `if [[ -s "$OUTPUT" ]]; then` block):
```bash
# Detect empty .result — distinct failure mode from missing .result.
if [[ -s "${OUTPUT}.json" ]] && command -v jq >/dev/null 2>&1; then
    if jq -e '.result == ""' "${OUTPUT}.json" >/dev/null 2>&1; then
        printf 'CURSOR_EMPTY_RESPONSE\n' > "$OUTPUT"
    fi
fi
```
This runs AFTER the existing extraction block, so non-empty `.result` (including the JSON sentinel) has already been promoted to $OUTPUT and this block is skipped for those cases.

### D. Collector update (`scripts/collect-agent-results.sh`)

In section 3.5 (around line ~934), change:
```bash
if [[ "$VAL_EXIT" -ne 0 ]]; then
    RESULTS[j]="...STATUS=NOT_SUBSTANTIVE..."
```
To:
```bash
if [[ "$VAL_EXIT" -eq 5 ]]; then
    RESULTS[j]="REVIEWER_FILE=$REVIEWER_FILE|TOOL=$ENTRY_TOOL|STATUS=CURSOR_EMPTY_RESPONSE|EXIT_CODE=0|HEALTHY=false|FAILURE_REASON=$DIAG_SAN"
    set_tool_unhealthy "$ENTRY_TOOL"
elif [[ "$VAL_EXIT" -ne 0 ]]; then
    RESULTS[j]="REVIEWER_FILE=$REVIEWER_FILE|TOOL=$ENTRY_TOOL|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|HEALTHY=false|FAILURE_REASON=$DIAG_SAN"
    set_tool_unhealthy "$ENTRY_TOOL"
fi
```

### E. Sibling .md updates
- `scripts/validate-research-output.md`: add JSON sentinel and CURSOR_EMPTY_RESPONSE to short-circuit list; document exit code 5 for CURSOR_EMPTY_RESPONSE
- `scripts/render-reviewer-prompt.md`: note JSON sentinel is canonical, NO_ISSUES_FOUND deprecated
- `skills/design/scripts/render-plan-review-prompt.md`: same

### F. Test harness updates

**`scripts/test-validate-research-output.sh`**: Add after case 19:
- Case 19b: `--validation-mode` + JSON sentinel literal → exit 0
- Case 19c: `--validation-mode` + JSON sentinel with extra keys → exit 0
- Case 19d: `--validation-mode` + JSON with no_issues_found:false → not short-circuited (falls to word-count)
- Case 19e: `--validation-mode` + JSON with no_issues_found as string "true" → not short-circuited
- Case 19f: `--validation-mode` + CURSOR_EMPTY_RESPONSE literal → exit 5
- Case 54b: structured-reviewer-mode + JSON sentinel → exit 0

**`scripts/test-render-reviewer-prompt.sh`**: Update line ~98 assertion from `NO_ISSUES_FOUND` to the JSON sentinel string.

**`scripts/test-launch-review.sh`**: Add a case (after Case B or near Case D) with `CURSOR_STUB_RESULT=""`:
- After the launcher runs, assert `$OUTPUT` contains exactly `CURSOR_EMPTY_RESPONSE`

**`scripts/test-collect-agent-bash32.sh`**: Add a case where the validator exits with code 5 → STATUS=CURSOR_EMPTY_RESPONSE.

**`skills/design/scripts/test-plan-review-prompt.sh`**: Update assertion from `NO_ISSUES_FOUND` to the JSON sentinel string.


## Test plan
1. `bash scripts/test-validate-research-output.sh`
2. `bash scripts/test-render-reviewer-prompt.sh`
3. `bash scripts/test-launch-review.sh`
4. `bash scripts/test-collect-agent-bash32.sh`
5. `/relevant-checks`
