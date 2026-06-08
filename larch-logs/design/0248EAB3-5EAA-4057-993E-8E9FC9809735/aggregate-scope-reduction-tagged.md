### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:45-46,106-117
- **Concern**: [SCOPE-REDUCTION] Plan allows making --prune-round-num mandatory while removing the review-round-count.txt fallback. Scenario: plan-review-loop.sh currently documents and supports omitted --prune-round-num; choosing the “fail when omitted” option would break direct single-pass callers that do not participate in the new Step 3 loop
- **Proposed resolution**: Keep --prune-round-num optional; when omitted set PRUNE_ROUND_NUM="$ROUND_NUM" without reading review-round-count.txt, while the shared Step 3 round body still passes the explicit review count
