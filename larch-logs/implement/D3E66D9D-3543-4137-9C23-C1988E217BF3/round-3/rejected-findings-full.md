### [rejected] FINDING_11

### FINDING_11: code-quality: scripts/test-dispatch-code-voters.sh:27-31
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Global unset vs spec subshell-per-test. Future test exports parent env: startup unset alone may not isolate. Use env -u per invocation or align spec to harness-wide unset.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: correctness: scripts/dispatch-code-voters.sh:171-177
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] larch_err now precedes issues-log resolution and append-tool-failure. Any tooling that assumed append-tool-failure ran before the stderr line may see reversed ordering. Restore prior ordering for non-suppressed runs if log scrapers depend on it; otherwise document the new order.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: scripts/test-dispatch-code-voters.sh:27-32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Feature text asked per-test subshell env isolation; code uses one global unset (matches written plan) Literal requirement/spec mismatch without observed leak in this harness Align spec to implementation or add subshell wrappers
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: .github/workflows/ci.yaml:26-34 and .github/workflows/release-tag.yaml:71-74
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Workflow-level FORCE_JAVASCRIPT_ACTIONS_TO_NODE24. Single incompatible action breaks every job in the workflow. Accept or narrow env to specific jobs if supported.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_22

### FINDING_22: risk-integration: scripts/test-dispatch-code-voters.sh:247-325
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry-fail fixtures no longer assert append-tool-failure / issues-log content. append-tool-failure broken or skipped: retry-fail tests can still pass via diag-only checks. Add stub invocation counter or keep one explicit issues-log assertion on a non-suppressed path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_23

### FINDING_23: risk-integration: scripts/test-dispatch-code-voters.sh:247-325
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] retry-fail fixtures dropped execution-issues assertions for parse-rate NOT_SUBSTANTIVE; only diag and KV are checked Regression in append-tool-failure wiring for the unset-LARCH harness-tmp branch might only surface in prod-shape regression3 with weaker localization Add stub append argv logging or one explicit non-harness REVIEW_TMPDIR case asserting issues-log lines for retry-fail
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0

### [rejected] FINDING_25

### FINDING_25: risk-integration: scripts/test-dispatch-code-voters.sh:315-319
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan asked for per-test subshell env isolation; implementation uses global unset at harness start Minor plan fidelity mismatch though child env assignments do not leak into parent Accept as doc-only or add explicit subshells if strict alignment matters
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_5

### FINDING_5: architecture: scripts/dispatch-code-voters.sh:296-335
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Voter1 failure append path has no harness suppression while parse-rate path does. Caller sets LARCH_EXECUTION_ISSUES_LOG to parent implement log and uses harness-shaped REVIEW_TMPDIR; voter1 empty/failure still appends to parent; parse-rate does not. Share suppression helper with voter1 failure branch or document intentional asymmetry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_6

### FINDING_6: architecture: scripts/test-dispatch-code-voters.sh:26-32
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature description Part (A) asks for per-case env-isolated subshells; harness uses one global unset at startup (matches written implementation plan, not the feature’s subshell wording). A future test exports SESSION_ENV_PATH or IMPLEMENT_TMPDIR into the harness shell; later cases inherit it unless they override. Add per-section subshells or repeat unset before each independent scenario block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: architecture: scripts/test-dispatch-code-voters.sh:315-320
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Startup unset replaces per-case subshell env isolation described in the plan. Future edits that export parent env vars after harness start could reintroduce leakage without subshell isolation at each invocation. Use per-invocation subshells or align documentation with the chosen isolation model.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/test-dispatch-code-voters.sh:17-20 (diff context)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan Part A asked for env-isolated subshells per test; harness uses one-time unset at startup instead. Reviewers comparing the branch to the written implementation_plan see a structural mismatch though behavior likely still fixes the leak. Update the plan wording after merge or add subshells only around blocks that export parent env vars if strict plan parity matters.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0

