### OOS_1: [OUT_OF_SCOPE] Combine-issues search can miss active work due to `--limit 100`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-combine-flow-logic-output.txt
- **Severity**: important
- **Concern**: `search-implementing-issue.sh` only inspects up to 100 GitHub search results before local filtering. If the relevant `[DESIGNING]` or `[IMPLEMENTING]` issue is outside that page, the helper can return `STATUS=none`, causing OOS actuality logic to discard an item as stale while implementation work is active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-combine-flow-logic-output.txt: Address the concern above.


