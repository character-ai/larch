### FINDING_12: [OUT_OF_SCOPE] Release Step 7 harness coverage is still missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-upgrade-flow-output.txt, dyn-harness-isolation-output.txt
- **Severity**: latent
- **Concern**: Release Step 7 root/state parsing remains a prompt-orchestrator contract without a dedicated `test-release-*` executable harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-upgrade-flow-output.txt, dyn-harness-isolation-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Cone matching ignores `known_marketplaces.json` `sparsePaths`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: JSON-only `sparsePaths` drift can be missed when the git sparse cone itself matches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] `get_installed_larch_version` lacks an empty-`HOME` guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Empty `HOME` can make installed metadata reads fail unpredictably.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_19: [OUT_OF_SCOPE] Standalone `/upgrade-larch` still uses the installed script path during bootstrap
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-fix installs may need a release/version bump before standalone `/upgrade-larch` picks up the fixed script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] Latest stable tag selection is not semver-sorted
- **Reviewer(s)**: dyn-upgrade-flow-output.txt
- **Severity**: latent
- **Concern**: `LATEST_STABLE` uses the first valid tag returned by `gh api`, which can misclassify upgrade state if tags are not sorted as expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upgrade-flow-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Step 8 restart state depends on fragile tempdir re-derivation
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: latent
- **Concern**: If the orchestrator loses the Step 2 temp artifact path, missing `release-step7.env` defaults both restart flags false and can silently skip restart guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] Upgrade script signal semantics still need tightening after verification failure
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: latent
- **Concern**: Same-version cone repair does not emit `LARCH_CONE_RECONCILED=true` when verification fails, even though the preamble was printed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Committed run-log files add unrelated diff noise
- **Reviewer(s)**: dyn-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: The branch includes committed `larch-logs/implement/...` run-log content unrelated to the harness changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] `NEW_VERSION_INSTALLED` glob remains brittle
- **Reviewer(s)**: dyn-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: The release Step 7 glob for new-version detection is fragile compared with explicit substring or machine-signal parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-isolation-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] Existing v47.0.70 sparse-cone symptom is operational debt
- **Reviewer(s)**: dyn-sparse-contract-output.txt
- **Severity**: latent
- **Concern**: The missing-`python/` marketplace cone symptom is pre-existing operational debt rather than a regression introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sparse-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_7: [OUT_OF_SCOPE] Security prune-trust docs still describe the old idempotent path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still says prune skips on already-latest idempotence without qualifying that same-version cone reconcile can now run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Docs and skill prose duplicate illustrative sparse literals
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt
- **Severity**: nit
- **Concern**: Installation docs, skills docs, and upgrade skill prose still include manual sparse-dir literals that can drift from `lib-sparse-dirs.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

