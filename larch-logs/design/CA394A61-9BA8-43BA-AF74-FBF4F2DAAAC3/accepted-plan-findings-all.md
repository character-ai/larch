### FINDING_3: Digest-size telemetry is not retained by GC
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: `checks-digest-sizes.tsv` is not in the GC keep set, so age-based slimming will delete historical telemetry before enough samples accumulate to compute the measurement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add checks-digest-sizes.tsv to implement/review SKILL_KEEP (and the Retention section in docs/run-logs.md) so measurement rows survive slim like token-report.json
  - From Cursor-Innovation: Add checks-digest-sizes.tsv to SKILL_KEEP for `implement` and `review` in `gc_run_logs.py` and document it in the Retention section of `docs/run-logs.md`.
  - From Codex-Pragmatic: Add checks-digest-sizes.tsv to the implement and review SKILL_KEEP sets, and cover retention in a gc-run-logs test.


### FINDING_4: Report parser rejects legitimate negative savings
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Concern**: Planned parser rejects the negative saved_* rows the plan says must be preserved, so genuine negative savings disappear and the report can never show true negative totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Store only unsigned source counts and derive savings in the report, or parse saved_bytes and saved_tokens as signed integers while still rejecting malformed rows


