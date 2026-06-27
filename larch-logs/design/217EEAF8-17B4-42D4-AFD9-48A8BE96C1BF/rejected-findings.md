### [Plan Review] FINDING_7

### FINDING_7: Default-path false-negative ingestion diverges from `--era` mode in voter-calibration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Failure modes require feeding both corpora through `_parse_file_into_stats()`, but implementation bullets only extend that helper for `--era` while default `main()` keeps a hand-rolled `voter_agreement_rows_from_tsv()` loop with "parallel" false-negative collection. Eligibility, malformed-row, or `_normalize_vote_cell` fixes can land in one path only, so default and `--era` false-negative tables diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Refactor default discovery to call `_parse_file_into_stats()` per discovered TSV (same as `_collect_era_corpora`), accumulating agreement and `false_negative_rows` from one helper; remove duplicated inline parsing in `main()`.


### [Plan Review] FINDING_8

### FINDING_8: Offline realized-outcomes success path lacks bulk-issues injection hook
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan adds `--filed-issue-details-json`, but the realized-outcomes section still needs a non-empty `issues` corpus to reach `ground_truth_voter_calibration()`. Without a CLI or test hook for the bulk issues JSON, the required success-path assertion cannot run deterministically offline and falls back to a live `gh issue list` dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a test-only way to inject the bulk `issues` corpus, or explicitly stub `gh issue list` in the harness, so the realized-outcomes success path is verifiable without network access.


