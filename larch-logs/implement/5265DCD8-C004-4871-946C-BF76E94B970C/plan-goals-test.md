## Goal
Loosen NO_ISSUES_FOUND sentinel check to first-non-empty-line match so reviewers with trailing operational notes are not wrongly rejected

## Implementation Plan

Loosen the NO_ISSUES_FOUND sentinel check in scripts/validate-research-output.sh to accept the sentinel as the first non-empty line instead of requiring it to be the entire trimmed file content.

### Files to modify:

**1. scripts/validate-research-output.sh**

Two locations require the same fix pattern:

a) Structured-reviewer-mode block (after `TRIMMED=$(trimmed_nonblank_content "$INPUT")`):
   - Add: `FIRST_LINE=$(printf '%s\n' "$TRIMMED" | awk 'NF { print; exit }')`
   - Change the NO_ISSUES_FOUND check from `[[ "$TRIMMED" == "NO_ISSUES_FOUND" ]]` to `[[ "$FIRST_LINE" == "NO_ISSUES_FOUND" ]]`
   - Change the jq invocation from `<<<"$TRIMMED"` to `<<<"$FIRST_LINE"` so the JSON sentinel check also operates on the first non-empty line

b) Validation-mode block (after `TRIMMED=$(trimmed_nonblank_content "$INPUT")`):
   - Add: `FIRST_LINE=$(printf '%s\n' "$TRIMMED" | awk 'NF { print; exit }')`
   - Keep `CURSOR_EMPTY_RESPONSE` check against `$TRIMMED` (full-content strict match required; no relaxation)
   - Change the NO_ISSUES_FOUND check from `[[ "$TRIMMED" == "NO_ISSUES_FOUND" ]]` to `[[ "$FIRST_LINE" == "NO_ISSUES_FOUND" ]]`
   - Change the jq invocation from `<<<"$TRIMMED"` to `<<<"$FIRST_LINE"`

c) Script header comment (line ~65-66): change "accepts a file whose entire trimmed content equals the canonical JSON sentinel ... or legacy NO_ISSUES_FOUND" to reflect first-non-empty-line matching.

d) Structured-reviewer-mode header comment (line ~82-83): same update.

**2. scripts/test-validate-research-output.sh**

Add 4 new regression cases (60-63) after the existing case 59:

- Case 60: --validation-mode, file = "NO_ISSUES_FOUND\n\nVerification: mktemp failed." → exit 0 (sentinel on first line, trailing note accepted)
- Case 61: --validation-mode, file = "Verification: mktemp failed.\n\nNO_ISSUES_FOUND" → exit 2 (sentinel NOT first line; body too thin, rejects as not-substantive; documents the choice)
- Case 62: --structured-reviewer-mode, same as 60 → exit 0
- Case 63: --structured-reviewer-mode, same as 61 reversed → exit 5 (sentinel NOT first; no valid records found)

Update header comment to list cases 60-63.

**3. scripts/validate-research-output.md**

Update the description of the NO_ISSUES_FOUND / JSON sentinel short-circuit from "entire trimmed content equals" to "first non-empty line equals", for both --validation-mode and --structured-reviewer-mode descriptions.

### Edge cases:
- Empty file: TRIMMED empty → FIRST_LINE empty → no sentinel match → falls through to word-count gate → exit 2 (backward compatible)
- Exactly "NO_ISSUES_FOUND" with no trailing content: FIRST_LINE = "NO_ISSUES_FOUND" → match (backward compatible)
- Trailing whitespace only: trimmed_nonblank_content already strips leading/trailing whitespace per its awk gsub rule → FIRST_LINE correctly unpadded

### Verification:
- Run `bash scripts/test-validate-research-output.sh` — all 63 cases must pass
- Run `make test-validate-research-output` to confirm Makefile wiring (already present, no changes needed)

## Test plan
(no test plan section in plan-file)
