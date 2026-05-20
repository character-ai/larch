### FINDING_1: **correctness** `scripts/compose-review-findings.sh:63-90` — After building `candidate`, the AWK compares it to the five tags with exact equality and never strips leading or trailing whitespace, unlike `extract_reviewer_from_body` (which trims). A reviewer-shaped title such as `code-quality : …` or `## **code-quality ** — …` yields a `candidate` with spaces and fails the whitelist, so a recognizable focus-area token can be dropped to an empty category. **Suggested fix:** Apply the same leading/trailing whitespace normalization to `candidate` before the whitelist `if` (for example `gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)` in the AWK block), or document that category matching is intentionally strict and whitespace-sensitive so consumers know empty categories can result from benign formatting.
- **Reviewer**: dyn-awk-logic-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:63-90` — After building `candidate`, the AWK compares it to the five tags with exact equality and never strips leading or trailing whitespace, unlike `extract_reviewer_from_body` (which trims). A reviewer-shaped title such as `code-quality : …` or `## **code-quality ** — …` yields a `candidate` with spaces and fails the whitelist, so a recognizable focus-area token can be dropped to an empty category. **Suggested fix:** Apply the same leading/trailing whitespace normalization to `candidate` before the whitelist `if` (for example `gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)` in the AWK block), or document that category matching is intentionally strict and whitespace-sensitive so consumers know empty categories can result from benign formatting.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/compose-review-findings.sh:63-90
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] candidate compared to whitelist without trimming trailing or leading whitespace If the first line is like '## code-quality : …' the colon branch yields 'code-quality ' which fails strict equality and category becomes empty though the tag name is present Trim whitespace around candidate before whitelist check; add a test if spaced colon form should count as valid
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/compose-review-findings.sh:64-87
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] extract_category whitelists candidate without trimming whitespace pending_title from OOS headers or Markdown can add leading/trailing spaces so a valid focus-area tag fails literal string match and category becomes empty JSONL strip leading/trailing whitespace on candidate in AWK before the five-tag comparisons
- **Suggested revision**: Address the concern above.


