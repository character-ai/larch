### FINDING_13: [OUT_OF_SCOPE] Pre-rebase flush proceeds after manifest recovery failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Python ship loop can exempt `REFRESH_SKIP_RECOVERY_FAILED` from stall gating and proceed into rebase/push work despite failed run-log manifest recovery, unlike stricter post-flush handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Postmerge report can be rendered before manifest done write
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `flush_logs_post` writes or renders final report artifacts before successfully writing `status=done`/`pr_number` to `manifest.json`, allowing summary output to claim completion while the manifest remains partial or failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Timing harness targets added to unrelated shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Unrelated Makefile timing harness changes increase CI time/flake risk on a finalize-focused branch without testing finalize behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] Merge parity lacks symmetric fail-closed gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Docs imply both merge and finalize bash parity fail closed, but merge parity can still all-skip green if module marks broaden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] `_write_ship_state` lacks newline validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: GitHub-derived KV fields written to `ship-pr-state.sh` are not newline-validated like finalize state, so multiline values could corrupt parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Orphan larch-log reset is authorized safety deviation
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Python intentionally requires non-empty subject evidence before orphan larch-log reset, unlike bash’s empty-loop shape; the reviewer marks this as documented and not a defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] Teardown ordering differs from bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Python writes cleanup/log-flush state before stall stash/sentinel work, while bash stashes first; cross-step ordering parity is not asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] Postbump rebase helper is not subprocess-pinned to bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: latent
- **Concern**: Python uses an inline `_rebase_no_push()` helper instead of routing through the bash parity wrapper, and its exit semantics are not subprocess-pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] `CI_FIX_REBASE_PENDING_HEAD` is diagnostic-only
- **Reviewer(s)**: dyn-state-write-mutation-output.txt
- **Severity**: nit
- **Concern**: `CI_FIX_REBASE_PENDING_HEAD` is written but not read by Python and has no bash equivalent; reviewer classifies it as diagnostic-only rather than current gating risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-write-mutation-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] `RESUME_PHASE` and `CALLER_KIND` are already cleared
- **Reviewer(s)**: dyn-state-write-mutation-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that `_write_ship_state` explicitly clears `RESUME_PHASE` and `CALLER_KIND`, addressing that specific scout concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-write-mutation-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] Postbump preflight treats empty symbolic-ref success as branch match
- **Reviewer(s)**: dyn-force-push-safety-output.txt
- **Severity**: latent
- **Concern**: `postbump_preflight` treats exit-0 empty `symbolic-ref` output as matching `ctx.branch_name`; reviewer notes later force-push validation mitigates this as looseness rather than direct bypass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-force-push-safety-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_36: [OUT_OF_SCOPE] `stage_and_push` does not compare HEAD branch to session branch
- **Reviewer(s)**: dyn-force-push-safety-output.txt
- **Severity**: latent
- **Concern**: `stage_and_push` derives the push branch from current HEAD instead of session branch state; current `force_push_recovery` checks mitigate this, but future mismatched callers could be risky.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-force-push-safety-output.txt: Address the concern above.

Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] README still says CI_FIX_REBASE_PENDING is omitted
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-write-mutation-output.txt
- **Severity**: important
- **Concern**: `python/README.md` documents Phase 6 as omitting `CI_FIX_REBASE_PENDING` even though this branch implements it, which can mislead operators and contributors about retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-write-mutation-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

