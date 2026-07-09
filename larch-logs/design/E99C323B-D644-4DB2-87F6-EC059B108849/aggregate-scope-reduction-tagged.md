### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_manifest.py
- **Concern**: [SCOPE-REDUCTION] Do not treat `.completed/step-3` alone as design plan-review reachability. Scenario: Pause log-publish keeps `.completed/step-3` without any `plan-review/round-*` tree (`python/tests/design/test_design_log_publish_flow.py::test_pause_log_publish_retains_completed_sentinels`). The planned OR with `plan-review/` makes `findings-classification.tsv` mandatory and `run-log commit` returns `RUN_LOG_INCOMPLETE_RC` on a path that succeeds today.
- **Proposed resolution**: Define `_design_plan_review_reached` only from committed `plan-review/round-*` evidence (e.g. at least one `findings-classification.tsv`). Do not key off `.completed/step-3` by itself; pause snapshots may retain that sentinel without plan-review artifacts.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/run_logs.py
- **Concern**: [SCOPE-REDUCTION] Limit the new waiver logic to the commit gate; do not re-emit required rows from `verify_completeness_main`. Scenario: Acceptance needs pre-commit enforcement with execution-issue waivers, not a behavior change to `run-log verify-completeness`. Rewiring `verify_completeness_main` to the new `RequiredArtifact` list risks drifting from `docs/run-logs-required-files.tsv` (e.g. `step5` still chains to `step7a` for `review-findings-full.jsonl`).
- **Proposed resolution**: Move shared reachability helpers only. Call `verify_run_log_completeness` from `_commit_run`. Keep `verify_completeness_main` on the TSV loop unless a test proves identical semantics.
