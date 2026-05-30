### FINDING_17: [OUT_OF_SCOPE] Automated commits run consumer-repo hooks without sandbox
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `git-commit.sh` runs target-repo hooks for every automated commit; this diff adds no hook sandbox. A compromised `.git/hooks` in the consumer repo can mutate the tree on each automated commit, including the new follow-up path. Trust model should be documented; hook isolation or selective `--no-verify` only where explicitly safe (not recommended globally).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] create-pr push guard uses full porcelain vs tracked-only Option B
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `create-pr.sh` push guard uses full porcelain while Option B re-check is tracked-only. Untracked-only residue after a round commit can block push but skip follow-up. Align checks or document the intentional split (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] CODER_STATUS=applied docs omit post-commit residue semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.md` line 25 documents `CODER_STATUS=applied` without post-commit residue / follow-up behavior that is only described later (e.g. line 56). Operators miss round-mode re-check and failure semantics—a pre-existing documentation gap.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Phase-14 resume skips pre-rebase fixup block
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Phase-14 resume paths skip the new pre-rebase fixup block. A dirty tracked tree on resume-after-conflict-resolution is not cleaned by this change; a shared fixup helper may be needed if resume can see dirty tracked trees.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Submodule inner dirty state blocks drop-bump under Option A
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Submodule-internal dirty state is not cleared by `git add -u` in the superproject; submodule entries can remain in porcelain, Option A is a no-op on the index, and Guard 1 still refuses drop. Pre-existing unless submodule policy changes.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

