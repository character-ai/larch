## Goal
Validate extract_category() output against 5 focus-area tags, returning empty for non-matching values; add regression tests for all 5 mangled-category shapes.

## Implementation Plan
Fix extract_category() to validate against 5 known focus-area tags and return empty for unrecognized values.


### Problem
`extract_category()` in `scripts/compose-review-findings.sh` extracts text from the first `## ` line of a finding body and returns it as the category. It does not validate that the extracted token is one of the 5 known focus-area tags (`code-quality`, `risk-integration`, `correctness`, `architecture`, `security`). This causes mangled categories when reviewers produce non-canonical heading shapes (reviewer-invented headings, file-path headings, pure prose paragraphs, comma-separated token lists).

### Fix

**`scripts/compose-review-findings.sh`** — replace the two `print` sites in `extract_category()`'s AWK body with a single `candidate` accumulation + validation block:

Current:
```awk
/^## / {
    sub(/^## /, "")
    if (substr($0, 1, 2) == "**") {
        sub(/^\*\*/, "")
        n = index($0, "**")
        if (n > 0) {
            print substr($0, 1, n - 1)   ← prints directly
        } else {
            print $0                       ← prints directly
        }
    } else {
        n = index($0, ":")
        if (n > 0) {
            print substr($0, 1, n - 1)   ← prints directly
        } else {
            print $0                       ← prints directly
        }
    }
    exit
}
```

Replacement: store extracted text in `candidate`, then print only if it is one of the 5 valid tags:
```awk
/^## / {
    sub(/^## /, "")
    if (substr($0, 1, 2) == "**") {
        sub(/^\*\*/, "")
        n = index($0, "**")
        if (n > 0) {
            candidate = substr($0, 1, n - 1)
        } else {
            candidate = $0
        }
    } else {
        n = index($0, ":")
        if (n > 0) {
            candidate = substr($0, 1, n - 1)
        } else {
            candidate = $0
        }
    }
    if (candidate == "code-quality" || candidate == "risk-integration" ||
        candidate == "correctness" || candidate == "architecture" ||
        candidate == "security") {
        print candidate
    }
    exit
}
```

This handles all 4 mangled-category failure modes from the issue:
1. Reviewer-invented headings (`TOCTOU:`, `Awk parsing:`) → candidate not in 5-tag set → empty
2. File-link-as-category (`` `scripts/create-pr.sh:40-43`: ``) → candidate not in set → empty
3. Pure-prose-paragraph (no `:`, entire line) → not in set → empty
4. Comma-separated token list (`docs, \`docs/voting-process.md\`:`) → candidate not in set → empty
5. Valid tags still pass unchanged.

**`scripts/test-compose-review-findings.sh`** — add a test section "mangled OOS categories return empty; valid tags pass" with:
- OOS oos.md fixture containing 6 findings covering shapes 3-6 (mangled) and valid `code-quality`, `architecture`, `security` tags (to augment existing `correctness` and `risk-integration` coverage)
- Assertions: valid tags produce the correct string; mangled shapes produce empty string

**`scripts/compose-review-findings.md`** — update the `category` field description to note the 5-tag validation constraint: add ", validated against the 5 known focus-area tags; empty when the extracted token is not a recognized tag" after the existing extraction description.

### Testing strategy
Run `make lint` or `bash scripts/test-compose-review-findings.sh` after the change to verify the harness passes.

## Test plan
(no test plan section in plan-file)
