### FINDING_2: Moving the summary table last can break first-line tolerance checks
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Printing the run-summary block or summary table after detail sections can move the first nonempty line away from the terminal summary heading, which breaks downstream tolerance logic that keys off that first line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: `Either keep a lightweight run-summary heading first, or update run_log_tolerance to locate the terminal run-summary heading anywhere in the file before evaluating it.`


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] The degraded write-failure path still appends issue detail after the existing summary body, so the new “summary last” contract is lost when `_write_enriched_post_publish_summary` hits OSError.
- **Description**: [OUT_OF_SCOPE] The degraded write-failure path still appends issue detail after the existing summary body, so the new “summary last” contract is lost when `_write_enriched_post_publish_summary` hits OSError.. Scenario: If the enriched rewrite fails, the fallback body can still publish `## /design run ...` before `## Review Phase Detail` and `## Exec Issues and Warnings`.
- **Reviewer**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/design/design_summary.py:313-330
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

