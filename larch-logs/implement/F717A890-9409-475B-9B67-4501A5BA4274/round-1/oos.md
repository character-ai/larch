### FINDING_10: [OUT_OF_SCOPE] broader acceptance matrix remains thin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt, dyn-branch-guard-output.txt
- **Severity**: latent
- **Concern**: Several plan-listed or pre-existing acceptance cases remain uncovered beyond this diff’s core scope, including cap behavior, stale local/GitHub routing, branch guards, marker preservation, and other Phase 7 scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt, dyn-branch-guard-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] done resume can skip postmerge for legacy state
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Legacy state with `PHASE=done` and GitHub `MERGED` can return OK without a postmerge flush; reviewers marked this out of scope because new forward paths write `done` only after postmerge succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] SECURITY.md overstates ship-state newline rejection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` claims newline rejection coverage that currently applies to finalize-state but not ship-pr-state; reviewers marked this doc/impl gap out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] manifest_status unused observation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt
- **Severity**: latent
- **Concern**: Multiple reviewers separately noted out-of-scope that `manifest_status()` is unused outside tests and may be a plan-only completeness gap rather than an immediate defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt, dyn-gh-authority-output.txt, dyn-mode-hydration-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_23: [OUT_OF_SCOPE] merge stall paths do not persist CI-loop counters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Merge stall returns may not persist iteration/rebase/fix counters, so re-invocation can reset budgets depending on resume classification; reviewers marked this as follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] gh.pr_view exception fresh fallback is an intentional trade-off
- **Reviewer(s)**: dyn-gh-authority-output.txt
- **Severity**: nit
- **Concern**: The broad `gh.pr_view` exception path trades transient handback for a fresh restart; reviewer marked this as an intentional plan trade-off rather than an accidental bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-authority-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] commit list observation
- **Reviewer(s)**: dyn-mode-hydration-output.txt
- **Severity**: nit
- **Concern**: Reviewer recorded the branch commits reviewed; this is an out-of-scope observation rather than a behavioral defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-mode-hydration-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] no-state path lacks entry-level protected-branch check
- **Reviewer(s)**: dyn-branch-guard-output.txt
- **Severity**: latent
- **Concern**: With no state file, `_resume_plan()` returns fresh without probing the current branch, so checks can run before later protected-branch guards; reviewer marked this defense-in-depth gap as largely pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-branch-guard-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] ship.py is a pre-existing large orchestrator
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `ship.py` was already a large orchestrator before this resume work; broader module splitting is a follow-up concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

