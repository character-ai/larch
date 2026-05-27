### [Plan Review] FINDING_4

### FINDING_4: File-replacement patch mode is premature scope
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Concern**: The plan adds `--patch-format file-replacement` as a second patch protocol even though current acceptance needs appear to require only unified diffs, increasing validation, docs, and test surface in a SIMPLE lane.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop --patch-format file-replacement and its test/docs branches for this PR; keep unified diff only unless the current caller requires replacement mode
  - From Cursor-Requirements: Keep only unified-diff for this piece unless the feature explicitly requires replacement mode; defer file-replacement to a follow-up if unified diffs prove brittle
  - From Codex-Requirements: Keep only unified-diff for this piece unless the feature explicitly requires replacement mode; defer file-replacement to a follow-up if unified diffs prove brittle


