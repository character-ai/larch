# Review Round 3

- Mode: `diff`
- 21 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_10: Malformed parsed JSON shapes can skip or miswarn
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-scan-semantics-output.txt
- **Severity**: important
- **Concern**: Parsed-but-invalid manifest or token-report JSON shapes such as `null`, arrays, strings, or empty objects can be skipped silently or warned as the wrong issue-number problem, violating fail-soft warning expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.


### FINDING_11: Codex/Cursor blended argv can underprice component-only totals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Codex/Cursor blended pricing uses `totals.total` without the component-sum fallback used for Claude, so reports with component token counts but `total == 0` can be underpriced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: Plot child accepts invalid schema, labels, and versions
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-plot-isolation-output.txt
- **Severity**: important
- **Concern**: `plot-cost-over-time.py` does not enforce the documented input schema, per-skill series counts/labels, point typing, or schema `version`, so malformed parent/child contracts can still produce PNGs with exit code 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-plot-isolation-output.txt: Address the concern above.


### FINDING_16: `relevant-checks.sh` misses report-tokens local regression targets
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ci-parity-output.txt
- **Severity**: important
- **Concern**: Relevant-checks routing does not cover all report-tokens Python, wrapper, plot script, and schema-doc surfaces, and lacks black-box regression tests for the new mappings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-ci-parity-output.txt: Address the concern above.


### FINDING_17: Plot parent/child contract tests are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-plot-isolation-output.txt
- **Severity**: important
- **Concern**: Plot tests do not fully assert the parent subprocess argv, written `plot-input.json`, implement/design series labels and counts, design smoke path, or persistent PNG output lifetime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-plot-isolation-output.txt: Address the concern above.


### FINDING_18: Plot child non-zero exit graceful-skip behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not verify that plot subprocess failures are handled as graceful skips with a stderr message and empty returned paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Empty scan CLI success path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no test for the “No parseable token reports found” exit-0 path, so empty-log handling can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: CLI `--no-issue` and `--no-plot` forwarding is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CLI tests do not verify that `--no-issue` prevents issue posting or that `--no-plot` prevents plotting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Golden markdown render tests are missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan asked for golden-file markdown tests, but implementation relies on inline substring assertions, leaving output-shape regressions harder to catch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_23: Actual-spend posted-section opt-in is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `POST_ACTUAL_SPEND` / `include_actual_spend_in_issue=True` behavior is not tested, so reconciliation content could leak or be omitted incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_24: Skill-specific issue titles are untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `title_for_skill` lacks tests for design and implement titles, so the GitHub issue title prefix can regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_25: Missing-started-at trend note is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover per-day trend notes for records with empty `started_at`, so missing-date accounting could regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_26: Quiet harness does not assert `Cache JSON:` stdout
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The quiet harness omits the acceptance check that stdout contains the cache JSON trailer for implement and design runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_28: Markdown table cells do not escape log-derived metacharacters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Phase step strings from token-report JSON are embedded in markdown tables without escaping pipes or newlines, allowing committed log data to corrupt or spoof public issue rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_30: Fallback pricing uses inconsistent token aggregation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `token-cost.sh` fails, fallback pricing uses `VendorTotals.total` instead of the bucket/component semantics used on the token-cost argv path, making fallback headline totals inconsistent and potentially wildly wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_31: Reports do not mark blended-fallback pricing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Runs priced by fallback/blended logic are aggregated with token-cost-priced runs without an in-report marker, so plausible tables can appear fully authoritative after partial pricing failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_33: Unknown workflow resolution lacks stderr warnings
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-scan-semantics-output.txt
- **Severity**: important
- **Concern**: Missing, unreadable, or classification-incomplete workflow artifacts default to `unknown` without the legacy warning signal, and design trend/plot code can then drop those runs from SIMPLE/HARD series.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.


### FINDING_34: Scan admission and pricing disagree on bucket-data validity
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: important
- **Concern**: `_has_numeric_tokens` can admit reports with positive non-schema bucket keys that pricing ignores, causing malformed-but-nonempty bucket objects to pass scan and then price near zero without a skip warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.


### FINDING_35: Claude aggregate token fallback omits `cache_create`
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: latent
- **Concern**: `_aggregate_tokens` sums split cache-create fields but not `VendorTotals.cache_create`, so reports with undivided cache-create totals can underfeed blended pricing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.


### FINDING_39: `gh issue create` failure details are not redacted
- **Reviewer(s)**: dyn-issue-posting-output.txt
- **Severity**: important
- **Concern**: On issue creation failure, stderr/stdout from `gh` is printed into the operator-visible error without redaction, unlike the success path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-posting-output.txt: Address the concern above.


### FINDING_44: `test-run-analysis-quiet` is missing from linting docs
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: latent
- **Concern**: `make test-run-analysis-quiet` is registered and sharded but lacks a `docs/linting.md` harness catalog row, leaving replay documentation incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.


