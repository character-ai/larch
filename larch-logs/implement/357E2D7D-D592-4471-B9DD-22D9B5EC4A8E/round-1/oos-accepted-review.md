### OOS_1: [OUT_OF_SCOPE] security: security-tagged dropped OOS committed to public run logs
- **Reviewer(s)**: codex-generalist-output.txt
- **Severity**: blocking
- **Concern**: The new allowlist commits `oos-dropped-before-vote.md`, but `_apply_pre_vote_oos_gate` writes every dropped OOS block into that file before any `voting.is_security_block` filtering. A reviewer can submit `### FINDING_1: [OUT_OF_SCOPE] [security] ...`, the pre-vote gate drops it, `_flush_round_log` preserves it in public `larch-logs`, and this bypasses the existing `SECURITY.md` local-only security-OOS boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist-output.txt: Split dropped OOS audit into public-safe and security-local artifacts, applying the same security-tag routing before parent copy or run-log allowlisting. Do not commit security-tagged dropped OOS content.


