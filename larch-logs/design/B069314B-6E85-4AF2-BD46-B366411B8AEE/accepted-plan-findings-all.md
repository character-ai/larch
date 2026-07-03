### FINDING_4: Stop gating standalone review capture on LARCH_TOKEN_SESSION_ID
- **Reviewer(s)**: Codex-dyn-Transcript Lifecycle
- **Severity**: blocking
- **Concern**: The review Step 0 prose still ties transcript materialization to `LARCH_TOKEN_SESSION_ID` and `SESSION_UUID` matching, so standalone review runs with a real Claude UUID can still leave `LARCH_CLAUDE_SOURCE_FILE` empty and skip capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Transcript Lifecycle: Remove the mismatch clause and bind LARCH_CLAUDE_SOURCE_FILE whenever token claude-source returns TRANSCRIPT_PATH=

