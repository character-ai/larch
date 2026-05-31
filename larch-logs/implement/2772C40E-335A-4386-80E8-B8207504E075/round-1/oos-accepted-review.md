### FINDING_16: [OUT_OF_SCOPE] External-coder round_dir write access to snapshots
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Codex dispatch grants write access to `$round_dir` alongside the repo root, so snapshot files written immediately before dispatch are not integrity-protected against a hostile external coder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Out of scope for #3272; a defense-in-depth improvement would snapshot to a read-only location the coder cannot reach, or re-read/recompute `pre-coder-head` and snapshots from git state after dispatch instead of trusting on-disk artifacts.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


