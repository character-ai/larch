### OOS_5: [OUT_OF_SCOPE] Codex exec prompt can leak through argv and metadata
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Codex exec prompt text is passed on argv and recorded in `CMD_JSON`. Session-scoped metadata and process listings may retain sensitive prompt text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


