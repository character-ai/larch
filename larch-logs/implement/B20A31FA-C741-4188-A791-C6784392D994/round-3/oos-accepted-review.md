### FINDING_17: [OUT_OF_SCOPE] Login fallback may symlink auth.json containing plaintext keys
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Login fallback symlinks `~/.codex/auth.json`, which may contain plaintext keys if created with `codex login --with-api-key`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


