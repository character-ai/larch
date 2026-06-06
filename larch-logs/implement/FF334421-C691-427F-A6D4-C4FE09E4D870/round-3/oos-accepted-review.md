### FINDING_12: [OUT_OF_SCOPE] Python default ships despite documented parity gaps
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-parity-contract-output.txt
- **Severity**: important
- **Concern**: The default Python ship driver is enabled while SECURITY.md documents unresolved parity/soak issues, exposing unset-`LARCH_SHIP_PR_IMPL` users to known gaps unless bash rollback is explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-parity-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_13: [OUT_OF_SCOPE] Empty/unset LARCH_SHIP_PR_IMPL default is only manually verified
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The empty-env default-to-Python behavior lacks CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_19: [OUT_OF_SCOPE] Missing focused RESUME_PHASE/CALLER_KIND preservation regression
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-coherence-output.txt
- **Severity**: nit
- **Concern**: Existing tests only partially cover preservation of resume tokens; there is no focused routine-refresh regression for non-empty `RESUME_PHASE`/`CALLER_KIND`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-state-coherence-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_20: [OUT_OF_SCOPE] write-final-report.sh state merge is outside plan traceability
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` now merges line-count KVs into `ship-pr-state.sh`, but that path was not in the plan file list, so rationale and acceptance coverage are unclear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] stall-recovery report does not use finalize-state.sh for phase fallback
- **Reviewer(s)**: dyn-state-coherence-output.txt
- **Severity**: latent
- **Concern**: `stall-recovery-report.sh` falls back to finalize for `stall_step` but not `phase`; reviewer notes this predates the branch and is unlikely to bite when terminal files stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-coherence-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_28: [OUT_OF_SCOPE] stall-recovery classify coverage already exists
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes existing tests cover finalize-only stall classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_29: [OUT_OF_SCOPE] Pre-push conflict handoff intentionally omits finalize-state.sh
- **Reviewer(s)**: dyn-parity-contract-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes the missing `finalize-state.sh` on `PrePushConflictHandoff` is intentional and bridged by Step 18 restore.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-parity-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_30: [OUT_OF_SCOPE] Recovery blockquote appears already fixed
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes the pre-fence recovery blockquote no longer contains the earlier bare inline `Invoke:` issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_31: [OUT_OF_SCOPE] NEVER #11/#13 and Step 18 restore read coherently
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes those rewrites appear coherent, with bash restoring when state exists and Python skipping when finalize is current.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_32: [OUT_OF_SCOPE] Harness does not pin several routing-prose regressions
- **Reviewer(s)**: dyn-routing-prose-output.txt
- **Severity**: nit
- **Concern**: Structure tests pin some selector behavior but do not assert absence of unqualified Exit 0 `ship-pr.sh`/`Invoke:` tails or the Exit 3 `BAIL_REASON` vs `needs_user_reason` split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-prose-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] Design/log artifacts inflate review surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Large design/log additions are unrelated to the ship-flip functional review surface and increase review and merge-conflict cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_8: [OUT_OF_SCOPE] NEVER #8 examples still cite only ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The examples drift from active-driver terminology by naming only `ship-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


