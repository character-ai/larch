# Review Round 2

- Mode: `diff`
- 12 accepted, 3 rejected (3 neutral)

## Accepted Findings

### FINDING_10: N-gram duplication omits Claude root imports
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `measure_ngram_duplication` no longer includes `CLAUDE.md` root imports such as `AGENTS.md` and `BASH_AUTHORING.md`, so prompt-loaded duplication is underreported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: References heatmap drops absolute and cache-derived Read paths
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `measure_references_heatmap` ignores absolute and cache-derived `Read` paths, which can make heatmap counts empty or incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Realized cost measurement dropped skill and issue normalization
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `measure_realized_cost` dropped skill normalization, manifest fallback, dev-skill lookup, and per-skill issue counting, so several skill invocations and issue observations can be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Token pytest parity is too thin for retired script coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required pytest parity for retired token scripts is largely missing, leaving core ledger, report, lane tally, append-record, and measure-helper behavior undercovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Timing pytest parity is too thin for retired harness behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required timing parity is mostly absent for lock timeout, harness mark, telemetry mark, record round, and workflow path isolation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Run-log batch write assertions are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_render_ledger_reports` tests do not assert `larch-log.sh write --batch token-report` and `timing-report` calls, so run-log batch writes could disappear while refresh JSON files still make tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: compute-pr-line-counts Make target no longer tests behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-compute-pr-line-counts` now runs `test_tokens.py`, but no `compute_pr_line_counts` pytest exists, so CI can report green without testing that behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Retained vendor scraper harness invokes a non-entrypoint Python file
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-token-vendor-scrapers.sh` calls `python/report_tokens_cost.py` directly even though it is not executable and has no script entrypoint, causing shard checks to fail before validating migrated token cost behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Direct report refresh is no longer best-effort on renderer failures
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Direct report refresh catches only `OSError` and `ValueError`, so unexpected renderer exceptions can abort pre-push refresh instead of preserving the old best-effort behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: Report format validation is missing
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Token and timing report paths accept unknown `--format` values and can silently render markdown into JSON-consumed files. Token append mode can also write Python dict repr when asked for JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Voting harnesses were deleted without parity coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Voting ballot and scoreboard shell harnesses were removed even though they are unrelated to the B2 token/timing migration and do not appear in `migrated-scripts.tsv`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Markdown cost tier classification regressed
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `measure_md_cost` collapses the old tier classifier, so root imports, Claude rules, dev skills, shared references, script docs, and run logs can be misclassified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


