### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1246-1256
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Other postmerge transitions (e.g. REPO_UNAVAILABLE, merge-skips) do not clear stall/bail keys. Rare combination of prior stall keys with these paths could still leave stale state for postmerge; unchanged by this branch. Consider a separate change if that scenario is realistic.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:1246-1256
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Skip-merge paths call advance_phase postmerge without clearing BAIL_REASON/STALL_TRACKING/STALL_STEP. Operator resumes ci-merge after a prior ci-merge stall; configuration forces early postmerge (e.g. MERGE=false or FORKED_TARGET=true). Stale bail/stall keys remain and can still flow into finalize artifacts and downstream bail checks like the bug fixed on merge-success paths. If parity is required, clear those keys on all transitions to postmerge or factor a single helper used by every postmerge entry.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.md:21
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New merge-success paragraph cites bare finalize-state.sh while nearby State docs use $IMPLEMENT_TMPDIR/finalize-state.sh; no scripts/finalize-state.sh exists. Readers may search the repo for the wrong path or misunderstand where finalize output lives. Use $IMPLEMENT_TMPDIR/finalize-state.sh or say tmpdir finalize-state payload for consistency with line 35.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-ship-pr.sh:440-459
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan text specified --resume-phase ci-merge; run_subject omits --resume-phase and only sets PHASE=ci-merge. Low risk today because ci-merge merge path does not depend on that flag for stubbed merge success; mismatch is mostly documentation fidelity. Optional: pass --resume-phase ci-merge from the harness or note intentional equivalence in a comment.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-ship-pr.sh:440-459
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test comments cite final-bail-reason.txt but assertions only cover state keys. If write_finalize_state ever diverged from read_state BAIL_REASON, the test would not catch it. Assert $IMPLEMENT_TMPDIR/final-bail-reason.txt is empty after PHASE=done.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/ship-pr.md:26-27
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New doc paragraph implies BAIL_REASON propagates into finalize-state.sh via write_finalize_state. Maintainer may search finalize-state.sh for stale bail text after a stall; BAIL_REASON is only written to final-bail-reason.txt in that function, not into finalize-state.sh. Split the explanation: BAIL_REASON to final-bail-reason.txt; STALL_* to finalize-state.sh.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/test-ship-pr.sh:443-458
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Regression test narrative and implementation plan call for `ship-pr.sh --resume-phase ci-merge`, but `run_subject` only runs ship-pr with state pre-set to PHASE=ci-merge (no `--resume-phase`). Plan-to-test traceability gap only; current harness behavior matches resume side effects for this template, so no demonstrated functional miss. Extend `run_subject` or this case to pass `--resume-phase ci-merge` (and keep stale stall keys in state) so the test matches the stated acceptance step.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-ship-pr.sh:283-290,444-459
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression harness does not pass --resume-phase ci-merge as specified in the plan; it relies on initial PHASE=ci-merge only. If resume handling ever diverges from a cold start at ci-merge (e.g. different state normalization), the test could pass while the operator path regresses. Have run_subject (or this case) invoke ship-pr.sh with --resume-phase ci-merge.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-ship-pr.sh:439-442
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comments describe --resume-phase ci-merge but run_subject does not pass that flag. Future edits may add a broken resume test or duplicate coverage while believing resume is already tested literally. Align comment with harness or add --resume-phase ci-merge to the invocation.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-ship-pr.sh:443-458
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Regression test covers only merge-pr merged success, not version_already_published+MERGED or already_merged actions. A future typo or conditional could drop clearing on one of the other two branches without failing CI. Add focused stubs for the other two success paths with pre-seeded stall state.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:444-459
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Stale stall-state regression is exercised only for MERGE_RESULT=merged; version_already_published+MERGED and ci-wait already_merged success paths are not tested with the same precondition. A mistaken edit removing clears from only one branch would not be caught by this test. Add compact tests for those branches with the same awk-injected stall keys.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:444-459
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test does not assert final-bail-reason.txt is empty after postmerge. If read_state and finalize file output ever diverged, state assertions alone might not catch a regression in write_finalize_state behavior. Assert IMPLEMENT_TMPDIR/final-bail-reason.txt is absent or empty after a successful run.
- **Suggested revision**: Address the concern above.

