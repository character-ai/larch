### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Concurrency acceptance for no per-PR bump is manual-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance for concurrency (second PR merges without rebase/re-bump; no bump/CHANGELOG commits) is manual-only. Regression reintroducing per-PR bump or DIRTY hot-spot conflicts would not be caught by updated harnesses until operators hit it in parallel PRs. Add a scripted two-branch fixture or document mandatory manual repro in CI/release checklist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: run_rebase_rebump skips ship-branch-guard without documented/tested rationale
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_rebase_rebump` intentionally skips `ship-branch-guard`; no test documents the relaxation. Wrong-branch CI-fix rebase could force-push without the guard that lived in `run_bump_phase`. Add a structural test or relocate minimal branch guard to the CI rebase entrypoint if parity is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: python/rebase.py retains rebase_and_rebump name after rebump removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Function name `rebase_and_rebump` persists after rebump removal. Phase 7 Python cutover readers may assume rebump still exists in this module. Rename to `rebase_and_push` (alias if needed) in a small follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: ship-pr.sh PHASE=bump label mislabels postbump-only work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PHASE=bump` label survives though the phase only runs postbump ship path. Log grep and resume docs reference "bump" for non-bump work. Optional rename to pre-ship/postbump in a later cleanup PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

