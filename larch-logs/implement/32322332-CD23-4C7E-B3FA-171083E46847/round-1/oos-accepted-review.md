### OOS_1: [OUT_OF_SCOPE] close-original lacks idempotency guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/decompose.py:276-319` — `close_original_issue` does not short-circuit when `.decompose-original-closed` already exists. After success it removes `.decompose-close-comment-posted`, so a direct `decompose close-original` re-run can post a duplicate partition comment. Pre-existing parity with the deleted shell helper; `decompose-panel.md` §0 guards the orchestrated path only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: early-return `CLOSE_ORIGINAL_STATUS=ok` when `.decompose-original-closed` is present.


