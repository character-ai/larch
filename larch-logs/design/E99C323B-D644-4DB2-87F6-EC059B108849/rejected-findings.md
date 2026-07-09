### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/report/run_logs.py
- **Concern**: [SCOPE-REDUCTION] Limit the new waiver logic to the commit gate; do not re-emit required rows from `verify_completeness_main`. Scenario: Acceptance needs pre-commit enforcement with execution-issue waivers, not a behavior change to `run-log verify-completeness`. Rewiring `verify_completeness_main` to the new `RequiredArtifact` list risks drifting from `docs/run-logs-required-files.tsv` (e.g. `step5` still chains to `step7a` for `review-findings-full.jsonl`).
- **Proposed resolution**: Move shared reachability helpers only. Call `verify_run_log_completeness` from `_commit_run`. Keep `verify_completeness_main` on the TSV loop unless a test proves identical semantics.


