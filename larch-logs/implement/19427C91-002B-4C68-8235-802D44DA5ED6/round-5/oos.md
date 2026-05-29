### FINDING_19: [OUT_OF_SCOPE] Prune `rm -rf` does not reject symlinked cache entries
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Prune `rm -rf` in `upgrade-larch.sh` (lines 176–184) does not reject symlinked version cache entries. A same-UID symlink under cache could redirect deletion outside the cache tree. Pre-existing; add `-L` checks or canonicalize before `rm` in a follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Implement tmpdir resolver scans `/tmp` without ownership checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `lib-resolve-implement-tmpdir.sh` (lines 29–54) scans `/tmp` `claude-implement-*` without ownership checks. A same-host attacker with writable `/tmp` could plant matching identity records (mitigated by cwd/session binding). Pre-existing; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Plan-expected `sessionstart-health.sh` keepalive comment not present
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan listed a comment-only update describing `.larch-keepalive` as a slim session-identity record in `scripts/sessionstart-health.sh`, but that file has no keepalive-related diff on this branch (only `SECURITY.md` and test fixtures were updated elsewhere). Maintainers reading the plan file list may expect in-script commentary that was never added. No functional gap, but plan fidelity is incomplete—add a short comment near the `lib-resolve-implement-tmpdir` invocation or amend the plan to name `SECURITY.md` as the sole canonical description.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] `get_stable_releases` picks first stable tag, not semver max
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `get_stable_releases` in `upgrade-larch.sh` (lines 49–66) picks the first API stable tag without semver max selection. Pre-existing and unrelated to #3174 retention redesign; future issue if tag ordering is not newest-first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

