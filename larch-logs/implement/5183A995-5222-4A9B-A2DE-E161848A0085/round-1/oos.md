### FINDING_14: [OUT_OF_SCOPE] architecture: bash apply-bump still hardcodes origin/main
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Bash `apply-bump.sh` still hardcodes `origin/main` while the Python port threads base through `apply_bump`. Intentional Python-side improvement beyond bash parity per plan Round 1; not required for this PR’s gap #2/#3 scope.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: default origin/main not asserted in new base test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Plan asked the new test to also assert default `origin/main` when base kwargs are omitted; only the upstream path is asserted in `test_apply_bump_threads_base` (`python/test_version_bump.py:540-601`). A regression that breaks default `base_remote`/`base_ref` might not be tied to the test name reviewers expect. Edge-cases notes defaults may be covered elsewhere in the file; still a minor coverage gap vs plan wording. Add a small default-base subcase, parametrize, or sibling case asserting `origin/main` fetch/show when kwargs are omitted.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] risk-integration: classify_bump still uses origin/main
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `classify_bump` still fetches/resolves against hardcoded `origin/main` (`python/version_bump.py:246-251` and classify path) while `rebase_and_rebump` / `apply_bump` can use another `base_remote`/`base_ref`. On fork/upstream rebump with e.g. `base_remote=upstream`, classification/merge-base can disagree with `apply_bump` guards and regression handling—wrong or inconsistent `bump_type`/`target_version` before guards correct some cases. Pre-existing gap; plan explicitly defers threading base into `classify_bump` (#3311 / separate follow-up). Track follow-up to thread `base_remote`/`base_ref` through `classify_bump` from `rebase_and_rebump` when fork-base end-to-end parity is required, or document partial base reconciliation until then.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] risk-integration: pre-drop refresh-run-logs / larch-logs fixup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bash refresh-run-logs pre-push/pre-drop fixup (`scripts/ship-pr.sh:3109-3112` and related rebump path) is not ported—gap #1. Dirty tracked `larch-logs/` can stall drop before rebase in bash; Python port lacks driver-owned fixup (`python/rebase.py:520-535`). Same class of failure: `drop_bump_commit` may return `dropped=false` and stall before rebase. Python path also omits refresh between rebump and push when logs are dirty around push time. Address in Phase 7 `ship.py` driver (#3240) before/alongside `rebase_and_rebump`; out of this PR scope.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] code-quality: has_bump naming collision
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `BumpPreCheck.has_bump` vs rebase `has_bump` param share a name with different semantics (`python/version_bump.py:58-60`). Code search or quick read can conflate skill presence with rebump gating. Consider renaming the rebase kwarg only if bash parity naming is not required; else document in module docstring.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

