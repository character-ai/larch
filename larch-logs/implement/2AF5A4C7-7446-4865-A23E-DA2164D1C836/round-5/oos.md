### FINDING_10: correctness: scripts/ci-decide.sh:134-146
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Phase 1 removes re-bump but ci-decide still emits ACTION=rebase when BEHIND_COUNT>0 and ship-pr still calls run_rebase_rebump. After concurrent PR merge B may still rebase in merge loop (without rebump), conflicting with strict no-rebase acceptance wording. Clarify Phase 1 acceptance as no-rebump only or implement merge-while-behind in Phase 2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/launch-codex-ci.sh:92-96` — Pre-existing pattern: when `--plan-file` is set, the full plan is embedded in the Codex CI-fix prompt via unbounded `$(cat "$PLAN_FILE")`. Plan text is treated as trusted in the launcher contract, but a hostile or compromised plan file is still prompt-injection surface for the external agent. Not introduced by this branch; unchanged in the diff hunk around the prompt build.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `scripts/ship-pr.sh:1072-1077`, `scripts/implement-finalize.sh:313-318` — Pre-existing trust model, now mirrored in postbump validation: `FORKED_TARGET=true` allows `BRANCH_NAME=main|master` through branch guards and into rebase/force-push. `FORKED_TARGET` is a boolean in session state under `$IMPLEMENT_TMPDIR`, documented as an operator/runbook trust signal with no cryptographic fork proof. Same-UID tmpdir tampering could theoretically steer a push; that is the repo’s stated session trust model (`SECURITY.md` / `ship-pr.md`), not a new class of bug from Phase 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `SECURITY.md` — The implementation plan lists `SECURITY.md` among docs to update when finalize/ship contracts change; this branch updates `implement-finalize.md` references but does not appear to revise `SECURITY.md` for retired bump-reasoning publication or postbump checkpoint semantics. Documentation drift only; no runtime exposure change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] risk-integration: scripts/launch-codex-ci.sh:3291-3298
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Codex quota signal mirrored from events JSONL to sidecar on failure (#3390). If events file is missing on failure, classification may still fall back to generic non-auth (pre-existing launcher edge). Ensure external_launcher_mirror_quota_from_events is fail-open when events path absent; already likely fine for this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] architecture: docs/linting.md:251
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Linting harness row still points to rebase-rebump-subprocedure.md for ci-wait synchronous-only rule; file is a retirement stub. Readers follow stale cross-ref and miss real ci-wait.md / SKILL.md guidance. Update linting.md and ci-wait.md site registry to current authorities (pre-existing drift amplified by stubbing).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **`ship-pr-rrr-phase14` re-entry looks sound:** conflict exhaustion sets `RESUME_PHASE` + `CALLER_KIND=ship_pr_pre_push`, writes `ship-pr-rrr-after-phase14.flag`, and stalls; resume requires `--resume-phase ship-pr-rrr-phase14`, valid `PHASE` (`ci-initial|ci-merge`), and the flag; `run_rebase_rebump` then short-circuits through verify + `_run_rebase_rebump_from_step3` (`2680-2685`). `scripts/test-ship-pr-rebase.sh` pins the structural tokens and the missing-flag guard (case E).
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **`ship-pr-rrr-phase14` re-entry looks sound:** conflict exhaustion sets `RESUME_PHASE` + `CALLER_KIND=ship_pr_pre_push`, writes `ship-pr-rrr-after-phase14.flag`, and stalls; resume requires `--resume-phase ship-pr-rrr-phase14`, valid `PHASE` (`ci-initial|ci-merge`), and the flag; `run_rebase_rebump` then short-circuits through verify + `_run_rebase_rebump_from_step3` (`2680-2685`). `scripts/test-ship-pr-rebase.sh` pins the structural tokens and the missing-flag guard (case E).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] **Harness gap:** `test-ship-pr-rebase.sh` does not exercise legacy `--resume-phase` tolerance (`bump`, `force-push-gate`, `step8b_rebase`) or state-file-only stale `RESUME_PHASE` without argv — worth adding if you tighten normalization.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **Harness gap:** `test-ship-pr-rebase.sh` does not exercise legacy `--resume-phase` tolerance (`bump`, `force-push-gate`, `step8b_rebase`) or state-file-only stale `RESUME_PHASE` without argv — worth adding if you tighten normalization.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] **`scripts/ship-pr.md:128`** still documents `REBASE_COUNT >= 5` while `run_rebase_rebump` uses `_max_rebases=20` (`2692-2693`); pre-existing doc drift, not introduced by the resume-compat slice.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **`scripts/ship-pr.md:128`** still documents `REBASE_COUNT >= 5` while `run_rebase_rebump` uses `_max_rebases=20` (`2692-2693`); pre-existing doc drift, not introduced by the resume-compat slice.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:34,50,56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NEVER tombstone entries for removed rules Longer NEVER list without adding enforcement Pre-existing style; optional cleanup in a docs-only follow-up
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

