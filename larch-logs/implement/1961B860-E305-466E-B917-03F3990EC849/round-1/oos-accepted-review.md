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


