## Decision 1: Fence-only scope; unfenced `### ` stays documented-behavior
- **Question**: Does this fix change how unfenced in-body `### ` lines are parsed?
- **Resolution**: No. The fix adds fence-awareness only. Unfenced in-body `### ` lines keep #2152's documented split-boundary behavior and its `parse-input:` breadcrumb unchanged. This issue supersedes #2152 for fenced content only.
- **Source**: codebase (issue #6676 body)

## Decision 2: Balanced-pair fence detection is load-bearing (not a naive toggle)
- **Question**: How are unclosed fences handled?
- **Resolution**: Pass 1 records line-index ranges of *balanced* fence pairs only. An opener that never closes degrades to plain text and does NOT fence the rest of the file, so later real `### ` boundaries still split. A naive open/close toggle is explicitly rejected (it reproduces the #3153 unclosed-trailing-fence failure).
- **Source**: codebase (issue #6676 work item 2; #3153 precedent)

## Decision 3: Byte-exact bodies, both generic and OOS paths
- **Question**: What is the correctness bar for parsed bodies?
- **Resolution**: A fenced item parses as ITEMS_TOTAL=1 with the body byte-identical to the input below the title line, including the full fence markers and info string. The OOS Description path must also stay one item when its Description carries a fenced `### ` line (issue flags OOS as likely-affected inference — verify while fixing).
- **Source**: codebase (issue #6676 acceptance criteria + root cause)

## Decision 4: Surface is surgical
- **Question**: Which files change?
- **Resolution**: `python/larch/issue/issue_create.py` (fence-aware `parse_issue_input`), `python/test_issue_create.py` (5 enumerated regression tests), and the `/issue` SKILL.md "Authoring caution (generic fallback)" block (narrow to unfenced only, keep the #2152 breadcrumb). No parser refactor beyond the two-pass insertion.
- **Source**: codebase (issue #6676 work items 1/3/4)
