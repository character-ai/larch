### FINDING_17: [OUT_OF_SCOPE] Plan review loop doc retains multi-round timing wording
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.md` still refers to “Multi-round mode” timing emission after the single-pass refactor. Runtime impact is harmless, but it is doc drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Exit-2 prose overstates abort behavior
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: On `run-step3-review.sh` exit 2, SKILL.md says it is aborting plan review, but control flow normalizes invalid/missing `LOOP_STATUS` to `panel-failed` and continues through the branch matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] Manual-requested production paths appear removed
- **Reviewer(s)**: dyn-shell-contract-output.txt
- **Severity**: nit
- **Concern**: Production shell paths no longer reference manual-requested/manual-gate-b fields or flags; stale `manual_gate_b` in restored run params is intentionally ignored and covered by structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Trailing public flags after numeric issue are intentionally ignored
- **Reviewer(s)**: dyn-shell-contract-output.txt
- **Severity**: nit
- **Concern**: Trailing public flags after a numeric issue are silently ignored by design, while leading manual flags correctly hard-fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] check-plan-size caller doc mentions removed post-revise path
- **Reviewer(s)**: dyn-drift-fence-output.txt
- **Severity**: nit
- **Concern**: `check-plan-size.md` still lists `plan-review-loop.sh` post-revise as a retained caller, but the single-pass refactor removed that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-fence-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Exact 2× drift boundary lacks regression coverage
- **Reviewer(s)**: dyn-drift-fence-output.txt
- **Severity**: nit
- **Concern**: Drift tests cover above-2× behavior but do not pin exact-2× strict-boundary behavior, even though the implementation appears consistent with the documented strict-`>` rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-fence-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] Top-level voter prompts remain publishable
- **Reviewer(s)**: dyn-artifact-boundary-output.txt
- **Severity**: latent
- **Concern**: Top-level plan voter prompt/output files remain publishable even though round staging excludes vote prompts. This is a pre-existing public-log boundary gap, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_33: [OUT_OF_SCOPE] Historical render-plan prompt logs remain committed
- **Reviewer(s)**: dyn-artifact-boundary-output.txt
- **Severity**: latent
- **Concern**: The branch blocks future publication of `render-plan-*.prompt`, but many historical committed prompt files remain in `larch-logs/design/`; scrubbing them is separate hygiene work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-boundary-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] Render-plan prompt deny coverage and Gate B explicit apply are security-positive
- **Reviewer(s)**: dyn-artifact-boundary-output.txt
- **Severity**: nit
- **Concern**: The branch adds regression coverage and docs for denying `render-plan-*.prompt` publication and improves security by removing inter-round auto-apply in favor of explicit Gate B approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-boundary-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] Orphaned revise helper and references remain
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-state-machine-output.txt, dyn-prompt-sync-output.txt
- **Severity**: latent
- **Concern**: `revise-plan-with-waterfall.sh` and related docs/tests/allowlists remain after Step 3 stopped invoking it, including docs that still describe it as a primary caller or retain structure pins. This is out-of-scope follow-up cleanup but may continue causing doc/tooling confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-state-machine-output.txt, dyn-prompt-sync-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

