### OOS_1: [OUT_OF_SCOPE] revise-plan-with-waterfall.sh orphaned after single-pass refactor
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Large helper remains in tree without Step 3 callers after single-pass refactor. Contributors may assume a live patch-apply path; dead code and SECURITY/publish allowlist complexity persist until follow-up removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove script docs and tests in planned follow-up issue.
  - From cursor-specialist-edge-cases-output.txt: Track removal in planned follow-up issue; no change required in this PR beyond current agent-lint exclude.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] design-step3-state.sh lacks .md contract file
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: No sibling `.md` contract file unlike other design script helpers. Harder for contributors to discover `STEP3_STATE` vocabulary and fail-closed rules without reading shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add design-step3-state.md mirroring other script contracts when committing the helper.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] design-postplan-emit.md exit 10 doc drift
- **Reviewer(s)**: dyn-drift-baseline-guard-output.txt
- **Severity**: nit
- **Concern**: `design-postplan-emit.md` still describes exit **10** as "plan-size skipped," but the implementation now runs plan-size on the defects-found + `--snapshot-original` path — doc drift only, not a runtime bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct fix direction beyond the concern; reviewer noted doc-only drift.)


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Missing harness pin for Gate A/C .step3-reentry marker write
- **Reviewer(s)**: dyn-pause-resume-sentinel-output.txt
- **Severity**: latent
- **Concern**: `assert_backward_reentry_guards` in `test-design-structure.sh:1674-1691` pins the Step 3 entry helper and Gate B/C stale-marker `rm` list, but does not pin that Gate A "Ready for review" / Gate C "Re-run review panel" prose actually writes `.step3-reentry` before Step 3, nor that sentinel mutations stay inside the helper's marker guard. Test-coverage gap rather than demonstrated runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Reviewer characterized as coverage gap only; no separate fix proposed beyond the concern.)

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

