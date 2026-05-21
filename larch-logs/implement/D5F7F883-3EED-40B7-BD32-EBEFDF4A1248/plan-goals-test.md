## Goal
Extract category from REJ_* JSONL rows by parsing triple-hash FINDING headers

## Implementation Plan

### Problem
`extract_category()` in `scripts/compose-review-findings.sh` uses an awk pattern that only matches `^## ` (two-hash) headings. Rejected findings (REJ_*) have prose bodies starting with `### FINDING_N: <category>: <location>` (three-hash, from the inner-heading accumulation path in `parse_artifact`). Result: `category=""` for all REJ_* JSONL records even when the category is present in the body.

### Files to change

1. **`scripts/compose-review-findings.sh`**:
   - Add a new awk rule `/^### FINDING_/` in `extract_category` that:
     - Strips `### FINDING_<id>:` prefix (using `sub(/^### FINDING_[^:]*:/, "")`)
     - Strips leading whitespace
     - Extracts candidate up to the next `:` (or whole remainder if none)
     - Applies same strict/non-strict whitelist logic
   - Update the function comment to mention the triple-hash format
   - Place the new rule BEFORE the `^## ` rule so it fires first when body starts with `### FINDING_`

2. **`scripts/test-compose-review-findings.sh`**:
   - Add a test case for REJ_* category extraction from `### FINDING_X: <category>: ...` bodies
   - Assert that `category` field is populated correctly for at least two canonical focus-area tags

3. **`.claude/skills/audit-runs/scans.tsv`**:
   - Add `rej-category-blank` row (jsonl-field type) that detects REJ_* records with blank category when prose_body contains a `### FINDING_N:` header

4. **`scripts/compose-review-findings.md`**:
   - Update `category` field description to mention `### FINDING_N: <category>:` (triple-hash) format for rejected findings

### Edge cases
- Empty first line in body (normal case): awk continues scanning until it hits the `### FINDING_N:` line
- No second colon in `### FINDING_N: <category>` (e.g., plain `architecture`): candidate = whole remainder after stripping
- Non-FINDING `### ` headings: pattern `/^### FINDING_/` won't match, falls through correctly
- Strict mode (OOS, strict=1): same whitelist check applies; not normally reached for REJ_* but correct anyway


## Test plan
Run `make test-compose-review-findings` (which runs `scripts/test-compose-review-findings.sh`) to confirm the new test passes and existing tests are unaffected.
