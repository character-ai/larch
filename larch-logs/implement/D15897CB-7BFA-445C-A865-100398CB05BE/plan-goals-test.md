## Goal
Rename /implement step 7a breadcrumb from 'code flow' to 'diagrams' for clarity

## Implementation Plan
Rename /implement step 7a breadcrumb text from "code flow" to "diagrams"

## Goal
Step 7a's current breadcrumb "code flow" is misleading — the step generates both the Code Flow Diagram and the Architecture Diagram and posts the larch:diagrams summary comment. "diagrams" better reflects the full scope of work.


### Files to modify

1. **skills/implement/scripts/step-name-registry.tsv**
   - Line 15: `7a\tcode flow` → `7a\tdiagrams`
   - (Line 16 `7a.r\trebase` is correct and unchanged)

2. **skills/implement/SKILL.md** — update all step-7a breadcrumb strings:
   a. Print line (step 7a entry): `Print: > **🔶 /implement 7a: code flow**` → `Print: > **🔶 /implement 7a: diagrams**`
   b. Quick-mode skip line: `⏩ 7a: code flow status=skip reason=quick-mode` → `⏩ 7a: diagrams status=skip reason=quick-mode`
   c. Small-non-runtime-change skip line: `⏩ 7a: code flow status=skip reason=small-non-runtime-change` → `⏩ 7a: diagrams status=skip reason=small-non-runtime-change`
   d. Rebase checkpoint macro call-site table entry: `| 7a.r | \`7a.r\` | \`code flow\` |` → `| 7a.r | \`7a.r\` | \`diagrams\` |`
   e. Rebase checkpoint macro invocation: `Apply the Rebase Checkpoint Macro with <step-prefix>=7a.r and <short-name>=code flow` → `Apply the Rebase Checkpoint Macro with <step-prefix>=7a.r and <short-name>=diagrams`


## Test plan
- `make lint` (or `/relevant-checks`) should pass
- `scripts/test-implement-rebase-macro.sh` checks the call-site registry table — update the expected value there too if it hardcodes the "code flow" string
- grep for remaining "7a: code flow" occurrences to ensure all are caught
