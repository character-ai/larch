### OOS_1: [OUT_OF_SCOPE] fix-loop integration section growth and CI timing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The fix-loop section in `scripts/test-ship-pr.sh` grows with two heavy ship-pr integration cases; shard 13/14 runtime may increase flakiness under tight CI budgets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monitor harness timing; split rebump cases to a dedicated section if needed


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] create-pr.sh push guards vs Option A ordering
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Push guards in `scripts/create-pr.sh` detect uncommitted changes before initial push; pre-existing recovery flows can commit dirty work before Option A runs at rebase. Interaction should be documented; no change required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document interaction; no change required for this PR.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Phase 14 resume skips pre-rebase fixup
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Phase 14 resume skips pre-flush and Option A fixup; a dirty tracked tree on `ship-pr-rrr-after-phase14` resume is not auto-committed before continuing re-bump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider running the same fixup block on resume if drop-bump will run later (separate change).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] CODER_STATUS=applied contract wording
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.md` still describes `CODER_STATUS=applied` in terms of post-dispatch dirtiness rather than post-commit tracked-tree cleanliness after round commits and follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update the contract line to describe final tracked-tree state after round-mode commits and follow-up.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

