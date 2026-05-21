## Goal
Fix plan-review-accepted FINDING rows to use canonical category instead of prose title in review-findings-full.jsonl

## Implementation Plan
Fix review-findings-full.jsonl: plan-review-accepted FINDING rows storing prose title as category field.

## Root Cause

`compose-review-findings.sh`'s `flush_pending` function prepends `## <prose-title>` to the body before calling `emit_record`. Inside `emit_record`, `extract_category` (with `strict_cat=0`) reads the first `## ` line and returns the prose title (or its pre-colon substring) as the `category` field. The actual `## canonical-category: location` line in `pending_body` is never reached because `extract_category` exits after the first `## ` match.


### 1. Fix `extract_category` in `scripts/compose-review-findings.sh`

In the `/^## /` awk rule, when `strict==1` and the parsed candidate is non-canonical, **remove the `exit`** and continue scanning. Currently both the canonical and non-canonical branches end with a shared `exit` at the bottom of the rule. New behavior:

```awk
/^## / {
    ... (candidate extraction unchanged) ...
    if (strict == 1) {
        if (is_canonical(candidate)) {
            print candidate
            exit
        }
        # Non-canonical in strict mode: skip and continue scanning
    } else if (candidate != "") {
        print candidate
        exit
    }
}
```

Use `is_canonical(candidate)` instead of the inlined repetition.

### 2. Set `strict_cat=1` for plan-review-accepted in `emit_record`

After the existing `[[ "$outcome" == "out_of_scope" ]] && strict_cat=1`, add:
```bash
[[ "$phase" == "plan-review" && "$outcome" == "accepted" ]] && strict_cat=1
```

### 3. Update test fixture and assertion in `scripts/test-compose-review-findings.sh`

Update `accepted-plan-findings.md` fixture to include a canonical `## architecture:` body line so the positive path is exercised:
```
### FINDING_1: Architecture boundary

## architecture: scripts/foo.sh

- **Concern**: scripts/foo.sh:42 does too much.
- **Resolution**: Split the helper.
```

Update assertion from `"Architecture boundary"` to `"architecture"`, and update the explanatory comment.

### 4. Update `scripts/compose-review-findings.md`

Update the `category` field description to document that `phase=plan-review outcome=accepted` rows use strict canonical filtering (non-canonical `##` tokens are skipped; scanning continues for a canonical `##` line).


## Test plan

Run `make test-compose-review-findings` to confirm the updated test passes. Also run `/relevant-checks` for full lint coverage.
