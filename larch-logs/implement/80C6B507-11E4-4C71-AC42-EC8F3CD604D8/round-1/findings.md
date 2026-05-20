### FINDING_1: **correctness** `scripts/compose-review-findings.sh:63-90` — After building `candidate`, the AWK compares it to the five tags with exact equality and never strips leading or trailing whitespace, unlike `extract_reviewer_from_body` (which trims). A reviewer-shaped title such as `code-quality : …` or `## **code-quality ** — …` yields a `candidate` with spaces and fails the whitelist, so a recognizable focus-area token can be dropped to an empty category. **Suggested fix:** Apply the same leading/trailing whitespace normalization to `candidate` before the whitelist `if` (for example `gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)` in the AWK block), or document that category matching is intentionally strict and whitespace-sensitive so consumers know empty categories can result from benign formatting.
- **Reviewer**: dyn-awk-logic-output.txt
- **Concern**: - **correctness** `scripts/compose-review-findings.sh:63-90` — After building `candidate`, the AWK compares it to the five tags with exact equality and never strips leading or trailing whitespace, unlike `extract_reviewer_from_body` (which trims). A reviewer-shaped title such as `code-quality : …` or `## **code-quality ** — …` yields a `candidate` with spaces and fails the whitelist, so a recognizable focus-area token can be dropped to an empty category. **Suggested fix:** Apply the same leading/trailing whitespace normalization to `candidate` before the whitelist `if` (for example `gsub(/^[[:space:]]+|[[:space:]]+$/, "", candidate)` in the AWK block), or document that category matching is intentionally strict and whitespace-sensitive so consumers know empty categories can result from benign formatting.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Commits on the branch (from `git log $(git merge-base HEAD main)..HEAD --oneline`): `2d5968e1 fix(compose-review-findings): whitelist extract_category focus-area tags`, `f9c82468 chore(larch-logs): flush implement run 80C6B507-11E4-4C71-AC42-EC8F3CD604D8`.
- **Reviewer**: dyn-awk-logic-output.txt
- **Concern**: - Commits on the branch (from `git log $(git merge-base HEAD main)..HEAD --oneline`): `2d5968e1 fix(compose-review-findings): whitelist extract_category focus-area tags`, `f9c82468 chore(larch-logs): flush implement run 80C6B507-11E4-4C71-AC42-EC8F3CD604D8`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] The branch diff also adds implement-session artifacts under `larch-logs/implement/80C6B507-11E4-4C71-AC42-EC8F3CD604D8/` (manifest, parent-issue, plan copies, tally JSON); that is unrelated noise next to the compose script fix and is easy to mistake for accidental `larch-logs` churn unless the repo intentionally commits those runs.
- **Reviewer**: dyn-awk-logic-output.txt
- **Concern**: - The branch diff also adds implement-session artifacts under `larch-logs/implement/80C6B507-11E4-4C71-AC42-EC8F3CD604D8/` (manifest, parent-issue, plan copies, tally JSON); that is unrelated noise next to the compose script fix and is easy to mistake for accidental `larch-logs` churn unless the repo intentionally commits those runs.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: scripts/compose-review-findings.sh:75-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] first-colon heuristic for category extraction pre-existed Headings with extra colons in paths or timestamps were already misparsed relative to prose 'category' Not required for this PR; any fix belongs to a dedicated parser change
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: larch-logs/implement/80C6B507-11E4-4C71-AC42-EC8F3CD604D8/plan-goals-test.md:116-118
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Flushed plan text says six OOS findings while tests use seven (four mangled plus three valid tags). Future readers comparing plan-goals-test.md to scripts/test-compose-review-findings.sh may think the fixture is underspecified or that a finding was dropped. Align wording to seven findings (or describe 4 mangled + 3 valid) on the next plan flush if parity matters; no code change required for behavior.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-compose-review-findings.sh:333-377
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] file-link fixture embeds path:line so category split hits an earlier colon The test still expects empty because the substring is not a known tag, not because the whole heading was validated as a file-link shape Use a path without an early colon or document/assert the intended substring semantics in the test
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/compose-review-findings.sh:63-90
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] candidate compared to whitelist without trimming trailing or leading whitespace If the first line is like '## code-quality : …' the colon branch yields 'code-quality ' which fails strict equality and category becomes empty though the tag name is present Trim whitespace around candidate before whitelist check; add a test if spaced colon form should count as valid
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/compose-review-findings.sh:64-87
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] extract_category whitelists candidate without trimming whitespace pending_title from OOS headers or Markdown can add leading/trailing spaces so a valid focus-area tag fails literal string match and category becomes empty JSONL strip leading/trailing whitespace on candidate in AWK before the five-tag comparisons
- **Suggested revision**: Address the concern above.

