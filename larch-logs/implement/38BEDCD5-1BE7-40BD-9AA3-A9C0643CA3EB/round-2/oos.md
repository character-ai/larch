### FINDING_11: [OUT_OF_SCOPE] Split unrelated PR line-count feature from scope-anchor work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-flow-output.txt, dyn-compat-mode-output.txt
- **Severity**: important
- **Concern**: The branch includes unrelated PR line-count/reporting changes alongside scope-anchor work, increasing review noise and isolation risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split features in PR description or separate commits/branches going forward.
  - From cursor-specialist-plan-fidelity-output.txt: Split #3506 into a separate PR or revert compute-pr-line-counts/render-run-summary/write-final-report changes from this branch
  - From dyn-scope-flow-output.txt: Address the concern above.
  - From dyn-compat-mode-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Add run-step3 IMPLEMENT_TMPDIR precedence test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: `test-run-step3-review.sh` does not prove `DESIGN_TMPDIR/feature-description.txt` wins over stale `IMPLEMENT_TMPDIR` state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub loop with decoy IMPLEMENT_TMPDIR; assert --feature-file uses DESIGN_TMPDIR/feature-description.txt.
  - From dyn-scope-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Happy-path scope-anchor wiring appears sound
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: nit
- **Concern**: Happy-path wiring uses the design feature file, materializes a staged scope anchor, forwards it to scout/panel/voters/revise, and preserves voter retry prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] Positive hardened prompt renderers
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: nit
- **Concern**: Reviewer, voter, and revise prompt renderers add untrusted-data framing plus redaction and HTML escaping for scope-anchor embedding, with breakout regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] Positive anchor materialization and handoff guards
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: nit
- **Concern**: Scope anchor materialization strips embedded plan blocks fail-closed, redacts secrets, rejects CR/LF paths, and constrains handoff under `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] Residual disclosure risk from wider issue-body inlining
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: latent
- **Concern**: `redact-secrets.sh` does not cover PII, internal URLs, or opaque bearer tokens, so wider issue-body inlining increases accidental disclosure risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] Document scope-anchor trust boundary in SECURITY.md
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` does not describe the new plan-review scope-anchor pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] Add collect-to-marker regression for severity-prefixed scope-reduction concerns
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: The collect path lacks a regression proving TSV `what:[SCOPE-REDUCTION]` or severity-prefixed `[SCOPE-REDUCTION]` Concern lines remain detectable downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fixture asserting collect output is detected by check-scope-reduction-marker.sh.
  - From cursor-specialist-testing-output.txt: Add test: collect output -> check-scope-reduction-marker.sh exit 0 for [important] [SCOPE-REDUCTION] Concern.
  - From dyn-marker-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_40: [OUT_OF_SCOPE] Add `--scope-anchor-file` to render-voter prompt flag docs
- **Reviewer(s)**: dyn-compat-mode-output.txt
- **Severity**: nit
- **Concern**: `render-voter-prompt.md` documents `--scope-anchor-file` in prose but omits it from the Flags table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-compat-mode-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_41: [OUT_OF_SCOPE] Positive compatibility isolation
- **Reviewer(s)**: dyn-compat-mode-output.txt
- **Severity**: nit
- **Concern**: Optional scope-anchor wiring appears isolated from code-review and no-flag voter defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-compat-mode-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] Unify duplicated scope-reduction marker detector entrypoints
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: `check-scope-reduction-marker.sh` duplicates the same Python detector for stdin and `--file`, creating drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify to one Python entrypoint reading argv path or stdin.
  - From dyn-bash-portability-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] Clean up unused/misleading `is_scope_reduction_block` API
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-marker-flow-output.txt, dyn-bash-portability-output.txt, dyn-compat-mode-output.txt
- **Severity**: latent
- **Concern**: `is_scope_reduction_block` is documented as shared tally surface but has no production callers and its parameter name suggests inline markdown even though it expects a file path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove wrapper or wire all marker checks through it; rename to block_file if kept.
  - From dyn-marker-flow-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Rename the parameter/doc to `block_file`, or write the block body to a `mktemp` under `$TMPDIR` and pass that path (with trap cleanup), matching how the Python deduper already invokes the helper.
  - From dyn-compat-mode-output.txt: Either wire the helper only where needed (dedup/aggregation) and trim the lib-vote-tally export/docs, or document it explicitly as test-only until tally consumes it.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

