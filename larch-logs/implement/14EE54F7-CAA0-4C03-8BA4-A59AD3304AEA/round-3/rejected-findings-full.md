### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: Pre- vs post-rebase verify exit-3 propagation diverges
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase verify exit 3 may kill ship-pr while post-rebase verify exit 3 in a subshell becomes return 1 and retries, diverging from planned exit-3 preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align exit-3 propagation or document and test intentional subshell behavior


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Duplicate BEHIND_COUNT parsing between ci-status and ship-pr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `ci-status.sh` parses `BEHIND_COUNT` with awk while ship-pr uses `kv_value`; future emit format changes could desync ci-wait gating from ship-pr push gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share kv_value parsing or a tiny behind-count-parse helper used by both scripts.
  - From cursor-specialist-plan-fidelity-output.txt: Optionally use kv_value for parity with ship-pr


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Large inline post-rebase block in `_stage_and_push_ci_fixes`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The rebase→reverify→stage→push sequence is hard to review and test in isolation inside one large inline block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a named helper for post-rebase reverify/stage; keep single push call site.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: #3175 anti-polling work bundled with #3210 on same branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unrelated hook/AGENTS changes ship in the same branch as CI-fix sequencing, forcing reviewers to validate out-of-scope surface to approve #3210.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split commits/PR sections or document explicit scope boundaries in PR summary.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: run-logs.md update cited in plan but absent on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance cites a run-logs doc update; branch omits it, so the run-logs contract may be stale relative to new CI-fix push sequencing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add run-logs note or remove criterion from issue


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: Inconsistent CI_FIX_REBASE_PENDING mutation style
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Push/verify paths mix direct `CI_FIX_REBASE_PENDING=` assignment with calls to an undefined `_ci_fix_rebase_pending_set` helper in some revisions, complicating review and risking runtime errors if helper calls land without a definition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Unify through one setter once defined


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: No harness for fetch-failure fail-open in ci-behind-count
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fetch failure always yields `BEHIND_COUNT=0` without regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub git fetch failure; assert BEHIND_COUNT=0 and diagnostic stderr


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Weak charset validation on ci-behind-count base CLI args
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pathological `base_remote`/`base_ref` strings reach git without the validation used in `run_rebase_rebump`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Share _validate_rebase_base_remote_ref or disallow .. and unsafe ref characters.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Fail-open BEHIND_COUNT=0 on git fetch/rev-list errors
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Transient `git fetch` or `rev-list` failure in `ci-behind-count.sh` emits `BEHIND_COUNT=0`; ship-pr may skip needed rebase and plain-push a fix still behind main, causing extra CI churn or pushing without integrating latest base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep fail-open for ci-status; optionally treat diagnostics in ship-pr push path as elevated Warnings or a conservative stall when push-time behind-check fails.
  - From cursor-specialist-security-output.txt: Fail closed on CI-fix push path or emit distinct unknown status; do not treat errors as zero behind.
  - From cursor-specialist-edge-cases-output.txt: Fail closed in CI-fix path or stall with diagnostic


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

