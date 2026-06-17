### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/review_test_support.py:406-422
- **Concern**: Ported review_core omits REVIEW_CORE_*_SH override contract that bash review-core and pytest stubs depend on. Scenario: review-core.sh routes gather/dispatch/collect/threshold through REVIEW_CORE_GATHER_CONTEXT_SH and siblings (python/legacy_review_shell/review-core.sh:83-91); build_review_core_env sets those to stub scripts for most review_core pytest. A native review_core that calls in-process helpers or cli.py without honoring the env overrides breaks the harness and fails make py-test.
- **Proposed resolution**: Add an explicit review_core port step: preserve the same REVIEW_CORE_*_SH subprocess override seams when the env var is set, or list and migrate every build_review_core_env test to monkeypatch the new native call sites before deleting review-core.sh.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/reviewer-prune.sh:59-297
- **Concern**: [SCOPE-REDUCTION] Plan treats reviewer-prune as a full bash port but the helper is already a thin bash argv wrapper around an inline Python heredoc. Scenario: Re-implementing from bash prose risks subtle ledger/filter drift versus today's behavior and adds unnecessary churn
- **Proposed resolution**: Lift the existing heredoc body into `review_pipeline.reviewer_prune` (plus `lib-prune-decision.sh` helpers); keep the new `review reviewer-prune` CLI as a thin argv relay

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-review-structure.sh:64-79
- **Concern**: Adding `review reviewer-prune` without updating the fixed-size verb registry will fail `make test-review-structure`. Scenario: The harness hard-codes `review_verbs` length 8 and greps `("review", "<verb>")` for each entry; registering the new CLI verb without bumping the count or appending `reviewer-prune` breaks assertion (1) on every `make lint` run
- **Proposed resolution**: In `scripts/test-review-structure.sh`, append `reviewer-prune` to `review_verbs`, change the expected length check from 8 to 9, and keep the `python/cli.py` registry grep loop in sync

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_test_support.py:406-454
- **Concern**: Plan does not define how native review_core replaces REVIEW_CORE_*_SH bash stub injection. Scenario: After review_core is in-process, build_review_core_env still points REVIEW_CORE_GATHER_CONTEXT_SH and siblings at executable bash stubs that review_core will no longer invoke; the listed review-core pytest matrix in python/test_review_pipeline.py will not exercise staged failures
- **Proposed resolution**: Add an explicit review_core testing contract: replace write_review_core_stubs/build_review_core_env/run_review_core with monkeypatch or injectable callables on review_pipeline stage functions (gather_context, dispatch_panel, collect_findings, check_reviewer_failure_threshold, aggregate/tally/emit façades, dispatch_voters); delete tests that read python/legacy_review_shell/review-core.sh source such as test_review_core_default_prune_nits_sh_points_at_skills_script
