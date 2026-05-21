### FINDING_17: [OUT_OF_SCOPE] Verbose `plan-goals-test.md` in committed run log tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-compat-output.txt
- **Concern**: Large low-signal markdown under `larch-logs/implement/.../` is policy/process noise for reviewers rather than a script defect.
- **Suggested revision**: Optional editorial trim of flushed plan content if desired.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] `write-final-report.sh` MERGE/PR/MERGE_RESULT fallthrough to unchanged “bailed”
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-existing structure behavior; not introduced by this branch’s outcome/render changes; no change required for this review scope.
- **Suggested revision**: None for this scope.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] `[[ ... ]]` in new `gh` stubs in `test-audit-runs.sh`
- **Reviewer(s)**: dyn-shell-compat-output.txt
- **Concern**: Valid on macOS Bash 3.2; not among constructs flagged by `scripts/lint-bash32.sh` (which scans `*.sh` only).
- **Suggested revision**: None.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] `.claude/skills/audit-runs/SKILL.md` still centers manifest `pr_number` skew
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: Skill-level guidance was not updated on this branch and can understate v2 “absent `pr_number` is normal” relative to `audit-scan-run.sh` `is_v2` behavior.
- **Suggested revision**: Follow-up doc/skill alignment if desired.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] `scripts/ship-pr.md` vs `scripts/implement-finalize.md` potential inconsistency
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: `ship-pr.md` still documents postmerge `status`/`pr_number` writes (consistent with `ship-pr.sh`) but may read as conflicting with finalize teardown doc after this branch.
- **Suggested revision**: Clarify split contract in a follow-up if policy is finalized elsewhere.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] `larch-log.sh` manifest does not forbid `pr_number`/`status` on `schema_version: 2`
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: Permissive-by-design for recovery/tests; schema cleanup remains a caller convention, not an enforced invariant.
- **Suggested revision**: Accept as policy or enforce in a separate change if product requires hard invariants.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] `scripts/larch-log.md` slightly overstates that `status` is never a post-init manifest concern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Recovery paths can still write `status=partial`; minor contract imprecision.
- **Suggested revision**: Clarify recovery exception in a follow-up doc edit.
```

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

