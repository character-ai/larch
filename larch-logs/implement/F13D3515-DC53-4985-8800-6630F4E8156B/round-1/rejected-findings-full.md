### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:556-575
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Edge-breadcrumb-count no longer tests dedicated LARCH_QUIET_BREADCRUMB_FD stream. Non-stdout breadcrumb FD regressions would not be caught in CI. Restore FD 9 (or separate) breadcrumb stream test in addition to FD 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: skills/implement/scripts/test-implement-bootstrap.sh:326-472
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Tracking-phase breadcrumbs not counted when LARCH_QUIET_BREADCRUMBS=1. Wrong or duplicate tracking breadcrumb strings could reach operators unnoticed. Add tracking breadcrumb count cases for adopt and skip branches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: scripts/implement-bootstrap.sh:379-388
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fork upstream context fetch is best-effort with || true. Failed gh fetch leaves empty upstream context files but the run continues under --forked, risking implementation against an incomplete upstream view. Emit UPSTREAM_CONTEXT_OK=false on failure and let SKILL abort or warn; or hard-bail when repo and issue were provided but fetch failed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: security: scripts/implement-bootstrap.sh:403-407
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Branch 1 mismatch check is gated on non-empty --issue-number. Omitting --issue-number while a sentinel exists resumes the sentinel issue number with no argv binding. Require --issue-number for Branch 1 or treat sentinel+empty argv as malformed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_28: risk-integration: scripts/implement-bootstrap.sh:460-472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] POSTED=false after successful larch-log init leaves orphan manifest without parent-issue.md sentinel. Deferred retry may create duplicate manifests or inconsistent RUN_ID across session retries. Document deferred orphan semantics or roll back manifest on POSTED failure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: architecture: scripts/implement-bootstrap.sh:382-388
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fork upstream context fetch requires both upstream repo and issue argv; failures are silent. forked_target=true without --upstream-repo skips context fetch with no hard error despite SKILL requiring UPSTREAM_REPO from implement-fork-env. die_usage or loud stderr when forked without upstream repo; align bootstrap validation with Protocol preflight.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: correctness: scripts/implement-bootstrap.sh:382-388
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fork upstream context fetch requires both upstream repo and issue-number argv. Fork bootstrap without --issue-number skips get-issue-context despite best-effort fork semantics. Call get-issue-context with repo only when issue absent, or require issue-number for forked-target in die_usage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: **architecture** `skills/implement/SKILL.md:414-419` — The compact “Bootstrap tracking bail routing” table covers all three script-emitted bail reasons (`adopted-issue-closed`, `adopted-issue-is-pr`, `tracking-init-failed` from `scripts/implement-bootstrap.sh:435-440` and `tracking_init_failed` at `138-141`), but it does not document the non-bail exit-2 path for unknown `STATE` (`scripts/implement-bootstrap.sh:442-444`), which is only described in the behavior map (`skills/implement/SKILL.md:577`) and exit-2 prose (`296-300`, `348-351`). That split is logically correct (no `IMPLEMENT_BAIL_REASON` on exit 2), yet an operator searching only the bail table may miss that `STATE=MERGED` (or any non-OPEN/non-CLOSED value) aborts via `STEP_FAILED=get-issue-state` rather than a bail token. **Suggested fix:** Add one row to the bail-routing table (or a sibling “exit 2” sub-table) stating “unknown/non-OPEN issue state → `STEP_FAILED=get-issue-state`, exit 2, abort Step 0” so all tracking outcomes are discoverable in one place.
- **Reviewer**: dyn-kv-protocol-consistency-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:414-419` — The compact “Bootstrap tracking bail routing” table covers all three script-emitted bail reasons (`adopted-issue-closed`, `adopted-issue-is-pr`, `tracking-init-failed` from `scripts/implement-bootstrap.sh:435-440` and `tracking_init_failed` at `138-141`), but it does not document the non-bail exit-2 path for unknown `STATE` (`scripts/implement-bootstrap.sh:442-444`), which is only described in the behavior map (`skills/implement/SKILL.md:577`) and exit-2 prose (`296-300`, `348-351`). That split is logically correct (no `IMPLEMENT_BAIL_REASON` on exit 2), yet an operator searching only the bail table may miss that `STATE=MERGED` (or any non-OPEN/non-CLOSED value) aborts via `STEP_FAILED=get-issue-state` rather than a bail token. **Suggested fix:** Add one row to the bail-routing table (or a sibling “exit 2” sub-table) stating “unknown/non-OPEN issue state → `STEP_FAILED=get-issue-state`, exit 2, abort Step 0” so all tracking outcomes are discoverable in one place.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:611-637
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Triplicated bail/stall guard before later phase stubs. Harder to maintain as plan/coder phases grow. Extract tracking_allows_later_phases helper used by plan/coder/all branches.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

