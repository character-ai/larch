## Goal
Fix OOS-finding category parser and title normalization for dynamic-reviewer bold-markdown format

## Implementation Plan

Fix three bugs in the OOS-finding pipeline when dynamic reviewers emit bold-markdown format headings.

### Files to modify

1. `scripts/compose-review-findings.sh` — fix `extract_category()` (lines 61-74)
2. `scripts/test-compose-review-findings.sh` — add regression test for bold-markdown OOS
3. `skills/review/scripts/collect-findings.sh` — normalize OOS bold-markdown titles in main findings loop
4. `skills/review/scripts/test-collect-findings.sh` — add regression test for title normalization
5. `scripts/compose-review-findings.md` — document bold-markdown format support
6. `skills/review/scripts/collect-findings.md` — document OOS title normalization

### Fix 1: extract_category() in scripts/compose-review-findings.sh

In the awk script (lines 61-74), add bold-markdown detection BEFORE the colon-split logic:

After `sub(/^## /, "")`, check `substr($0, 1, 2) == "**"`:
- If true: strip leading `**` with `sub(/^\*\*/, "")`, then find closing `**` via `index($0, "**")`, print `substr($0, 1, n-1)` and `exit`.
- If false: fall through to existing `index($0, ":")` colon-split logic.

Uses only POSIX awk (no GNU extensions). Backward-compatible: static `## risk-integration: file:lines` format has no leading `**` so it falls through to existing logic unchanged.

### Fix 2: OOS title normalization in skills/review/scripts/collect-findings.sh

In the bash while-read findings loop (around line 391, after `count=$((count + 1))`), add normalization BEFORE writing to `FINDINGS_FILE` and `OOS_FILE`:

```bash
if [[ "$title" == "[OUT_OF_SCOPE] **"* ]]; then
    oos_body="${title#[OUT_OF_SCOPE] **}"
    category="${oos_body%%\*\**}"
    fileref=""
    if [[ "$title" =~ \[\`([^\`]+)\`\] ]]; then
        fileref="${BASH_REMATCH[1]}"
    fi
    if [[ -n "$fileref" ]]; then
        title="[OUT_OF_SCOPE] $category: $fileref"
    else
        title="[OUT_OF_SCOPE] $category"
    fi
fi
```

Keeps `[OUT_OF_SCOPE]` prefix unchanged so downstream checks (`[[ "$title" == \[OUT_OF_SCOPE\]* ]]`) still work.

### Fix 3: Regression tests

In `scripts/test-compose-review-findings.sh`: add test with bold-markdown OOS entry in `oos.md`, assert:
- `category == "risk-integration"` (not truncated markdown leak)
- Backward-compat: static `## risk-integration: file:lines` format still extracts correctly

In `skills/review/scripts/test-collect-findings.sh`: add test with bold-markdown OOS bullet in reviewer output, assert:
- Normalized short title in `findings.md` (not sprawling version)
- `OOS_COUNT=1`

### Fix 4: Update companion .md files

- `scripts/compose-review-findings.md`: note that `extract_category()` handles both static `## cat: file:lines` format AND dynamic bold-markdown `## **cat** — [\`file\`](...)` format.
- `skills/review/scripts/collect-findings.md`: document that OOS titles with bold-markdown+bracketed-link format are normalized to `[OUT_OF_SCOPE] category: file:lines` before writing to findings and oos files.

### Testing strategy

Run `make lint` (which includes `bash test-compose-review-findings.sh` and `bash test-collect-findings.sh` via pre-commit). Run `/relevant-checks` after implementation.

### Edge cases

- Title starts with `[OUT_OF_SCOPE] **` but has no closing `**` pair: `category` will be the entire `oos_body` (safe fallback).
- Title starts with `[OUT_OF_SCOPE] **` but has no backtick-link `[\`...\`]`: `fileref=""` → title = `[OUT_OF_SCOPE] $category` (safe fallback).
- Bold-markdown with `**` but no closing `**` in extract_category: `n=0` → print `$0` (existing fallback path).

## Test plan
(no test plan section in plan-file)
