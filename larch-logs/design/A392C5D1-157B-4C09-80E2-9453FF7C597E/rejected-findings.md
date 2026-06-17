### [Plan Review] FINDING_1

### FINDING_1: Native review_core must preserve or migrate REVIEW_CORE_*_SH stub contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The port of `review_core` to in-process Python does not define how the existing `REVIEW_CORE_*_SH` override contract is honored. Bash `review-core.sh` routes gather/dispatch/collect/threshold through env vars such as `REVIEW_CORE_GATHER_CONTEXT_SH` (see `python/legacy_review_shell/review-core.sh:83-91`). `build_review_core_env` in `python/review_test_support.py` sets those vars to stub scripts for most `review_core` pytest coverage. A native implementation that calls in-process helpers or `cli.py` without honoring those overrides when set will break the harness and can fail `make py-test`. After the port, stubs may remain configured but never invoked, so the listed `review-core` pytest matrix in `python/test_review_pipeline.py` will not exercise staged failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit review_core port step: preserve the same REVIEW_CORE_*_SH subprocess override seams when the env var is set, or list and migrate every build_review_core_env test to monkeypatch the new native call sites before deleting review-core.sh.
  - From Cursor-Requirements: Add an explicit review_core testing contract: replace write_review_core_stubs/build_review_core_env/run_review_core with monkeypatch or injectable callables on review_pipeline stage functions (gather_context, dispatch_panel, collect_findings, check_reviewer_failure_threshold, aggregate/tally/emit façades, dispatch_voters); delete tests that read python/legacy_review_shell/review-core.sh source such as test_review_core_default_prune_nits_sh_points_at_skills_script


### [Plan Review] FINDING_2

### FINDING_2: `reviewer-prune` verb must update fixed-size review verb registry
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Adding `review reviewer-prune` without updating the fixed-size verb registry in `scripts/test-review-structure.sh` will fail `make test-review-structure`. The harness hard-codes `review_verbs` length 8 and greps `("review", "<verb>")` for each entry; registering the new CLI verb without bumping the count or appending `reviewer-prune` breaks assertion (1) on every `make lint` run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `scripts/test-review-structure.sh`, append `reviewer-prune` to `review_verbs`, change the expected length check from 8 to 9, and keep the `python/cli.py` registry grep loop in sync

**Merge notes**: Cursor-Arch and Cursor-Requirements both target the same behavioral gap (stub/override contract for native `review_core` and its pytest harness). Severity merged to **blocking** per rule. Cursor-Pragmatic is a separate integration risk on the lint harness verb registry and stays as FINDING_2.


### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/reviewer-prune.sh:59-297
- **Concern**: [SCOPE-REDUCTION] Plan treats reviewer-prune as a full bash port but the helper is already a thin bash argv wrapper around an inline Python heredoc. Scenario: Re-implementing from bash prose risks subtle ledger/filter drift versus today's behavior and adds unnecessary churn
- **Proposed resolution**: Lift the existing heredoc body into `review_pipeline.reviewer_prune` (plus `lib-prune-decision.sh` helpers); keep the new `review reviewer-prune` CLI as a thin argv relay

