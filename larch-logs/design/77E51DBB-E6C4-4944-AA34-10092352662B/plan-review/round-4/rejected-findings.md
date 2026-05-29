### [Plan Review] FINDING_4

### FINDING_4: Cross-doc trailer grammar may diverge across consumer-facing surfaces
- **Reviewer(s)**: Cursor-dyn-cross-doc-trailer-contract, Codex-dyn-cross-doc-trailer-contract
- **Severity**: important
- **Concern**: The plan centralizes the full optional trailer grammar and scan contract in `check-plan-size.md`, while other edited surfaces receive only partial summaries or references. This can leave consumers with inconsistent rules for accepted regexes, blank-line stopping, duplicate-key precedence, and `PLAN_LINES` subtraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-trailer-contract, Codex-dyn-cross-doc-trailer-contract: Add the same compact canonical contract to each touched prose surface: exact three regexes, final contiguous block immediately above final diff_lines, stop at first non-matching line including blanks, malformed lines absent and stop scanning, duplicate keys last in file order closest to diff_lines, and PLAN_LINES subtracts only recognized optional metadata trailers. Keep check-plan-size.md authoritative, but do not rely on cross-reference alone.


