### FINDING_11: [OUT_OF_SCOPE] Uncommitted trailer-harness improvements not on HEAD
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Local working-tree edits add octal-then-valid and keys assertions for octal-rejected but are not on HEAD or the review diff snapshot; merge without commit understates coverage on the remote branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Commit or drop the unstaged harness hunk before merge.
  - From cursor-specialist-plan-fidelity-output.txt: Commit or drop local harness deltas before merge


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] `write_fixture` does not validate fixture names
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `write_fixture` does not validate fixture names for path traversal. Only hardcoded names are used today; no current exploit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject names containing / or .. if dynamic names are added later.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] `--dedup` grep in `test-design-structure.sh` not pipeline-anchored
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `--dedup` grep is anywhere-in-file, not pipeline-anchored; a doc-only `--dedup` mention could satisfy the pin without a runnable hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional follow-up: anchor greps to gate-b-dedup-plan.sh invocations (pre-existing pattern).


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] Branch bundles unrelated commits beyond #3204
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Branch bundles unrelated commits beyond the #3204 plan; PR reviewers may treat version/cleanup/ship-pr changes as part of trailer work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Keep #3204 commit isolated or split PRs


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### FINDING_5: [OUT_OF_SCOPE] Duplicated hook-residue commit logic in review-and-fix vs ship-pr
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Hook-residue commit logic is duplicated between `review-and-fix.sh` and ship-pr pre-rebase fixup (#3209); the two sites can diverge on staging scope or failure handling over future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a small shared helper when next touching residue fixup (optional refactor)


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] Cleanup #3212 top-level `find -mtime` tradeoff (documented)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: #3212 trades nested activity scan for top-level `find -mtime`; age semantics differ from the prior depth-5 activity model. Already documented in cleanup SKILL; no action needed for #3204.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] Cleanup drops nested-activity retention model
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Cleanup uses directory mtime only, not nested activity. An active session directory with an old root mtime but fresh nested files may be deleted after retention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document tradeoff or bounded nested mtime without unbounded find.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Round follow-up residue check ignores untracked files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The follow-up residue check ignores untracked files; untracked-only hook residue after the round commit may still report `CODER_STATUS=applied`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Extend check or document reliance on ship-pr backstop explicitly.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

