### FINDING_1: [OUT_OF_SCOPE] `_posting_body` applies redaction more than once
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-posting-output.txt
- **Severity**: important
- **Concern**: Issue posting applies `redact.redact()` more than once, so trim sizing and body posting no longer follow the documented single-redaction-pass contract; redundant passes are harmless only if redaction remains perfectly idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-issue-posting-output.txt: Address the concern above.

### FINDING_2: Display titles are duplicated and coupled to internal section keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Reader-facing section titles are duplicated between render output and `_TITLE_BY_SECTION`, while `ReportSection.title` appears to hold internal slugs; header renames can leave stale trim notices or internal keys in output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Implement/design grouping logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Render tables and plot series duplicate skill-specific aggregation/filtering, so implement/design behavior can diverge after a one-sided edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] `SectionPriority.BANNER` is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-posting-output.txt
- **Severity**: latent
- **Concern**: The trim contract documents a banner priority, but no rendered `ReportSection` uses `SectionPriority.BANNER`; banner text is assembled outside the section list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-issue-posting-output.txt: Address the concern above.

### FINDING_5: Duplicate `_as_mapping` helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scan` and `cost` define duplicate mapping coercion helpers, creating drift risk for edge-case JSON typing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Duplicate date helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Render and plot duplicate date parsing helpers, so date behavior changes require synchronized edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Env boolean parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: CLI and plot env-boolean parsing duplicates existing `run_context._env_bool` semantics and could disagree on enabled values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Exit code constants alias value 4
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `EXIT_BAIL` and `EXIT_STALLED` share value `4`; reviewer marked this as pre-existing config aliasing unrelated to report-tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Test fake-runner boilerplate is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Per-file fake runner dataclasses duplicate test boilerplate, but this is a pre-existing test pattern outside the report-tokens plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_13: [OUT_OF_SCOPE] Ship-pr Phase 7 paths were not reviewed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Ship-pr Phase 7 driver changes appear in the branch diff but were outside the report-tokens-focused correctness pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] `LARCH_REPORT_TOKENS_LIMIT` counts directories, not parsed records
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-semantics-output.txt
- **Severity**: latent
- **Concern**: The limit can stop after lexicographically early junk directories and skip later valid runs; reviewers marked this as pre-existing or plan-out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Plot dates and per-day table dates use different fields
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-pricing-pipeline-output.txt, dyn-scan-semantics-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Plots use `closed_at` while per-day tables use `started_at`, so the same run can land on different dates; reviewers marked this as a preserved legacy quirk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-pricing-pipeline-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.
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

### FINDING_20: [OUT_OF_SCOPE] Bad manifest/token-report scan fixtures are incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-scan-semantics-output.txt
- **Severity**: important
- **Concern**: Plan-listed malformed manifest and token-report fixtures are missing or incomplete, especially invalid syntax, `null`, non-object, and empty-object cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-scan-semantics-output.txt: Address the concern above.

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

### FINDING_27: [OUT_OF_SCOPE] Ship-pr parity target increases harness shard load
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-merge-parity` bundled in the same branch may affect shard timing, but reviewers marked this as unrelated ship-pr work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_28: Markdown table cells do not escape log-derived metacharacters
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Phase step strings from token-report JSON are embedded in markdown tables without escaping pipes or newlines, allowing committed log data to corrupt or spoof public issue rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_29: Full analysis stdout is not redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The CLI prints full markdown to stdout without applying the same redaction used for issue bodies, so sensitive phase names or paths can leak to CI/operator transcripts.
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

### FINDING_32: Truncation notice overemphasizes `--no-issue`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The truncation banner tells issue readers to rerun with `--no-issue` even though the normal invocation already printed the full analysis to stdout.
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

### FINDING_36: [OUT_OF_SCOPE] Mixed bucket/blended argv behavior matches the plan
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that per-vendor mixed bucket/blended argv behavior is correct and improves on the removed bash all-or-blended gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Cost env forwarding matches the documented contract
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that forwarding `LARCH_RATE_*` and legacy aliases into `token-cost.sh` matches the documented contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Design summaries include unknown workflow runs that trend/plot series omit
- **Reviewer(s)**: dyn-pricing-pipeline-output.txt
- **Severity**: latent
- **Concern**: Design-mode summary totals can include `unknown` workflow runs while SIMPLE/HARD trend tables and plots omit them; reviewer marked this as a pre-existing plan quirk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pricing-pipeline-output.txt: Address the concern above.

### FINDING_39: `gh issue create` failure details are not redacted
- **Reviewer(s)**: dyn-issue-posting-output.txt
- **Severity**: important
- **Concern**: On issue creation failure, stderr/stdout from `gh` is printed into the operator-visible error without redaction, unlike the success path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-posting-output.txt: Address the concern above.

### FINDING_40: Issue-post failure can look like a successful analysis artifact
- **Reviewer(s)**: dyn-issue-posting-output.txt
- **Severity**: latent
- **Concern**: The CLI prints the full analysis and cache trailer before posting; if posting fails, callers that grep stdout but ignore exit status may treat the run as fully successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-posting-output.txt: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Issue/plot stdout lines drift from cache-trailer contract
- **Reviewer(s)**: dyn-issue-posting-output.txt
- **Severity**: latent
- **Concern**: Successful issue-post output and plot status lines append stdout after the analysis/cache trailer, mixing operational metadata with the analysis artifact; reviewer also noted adjacent pre-existing plot stdout drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-posting-output.txt: Address the concern above.

### FINDING_42: Plot subprocess has no timeout
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: The matplotlib child runs via `runner.run(...)` without a timeout, so a hung or pathological plot run can block `/report-tokens`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] Plot `open` result is unchecked
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: `report_tokens_plot.py` invokes `open` through the runner without checking the result; reviewer marked this as a minor operational gap outside matplotlib isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_44: `test-run-analysis-quiet` is missing from linting docs
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: latent
- **Concern**: `make test-run-analysis-quiet` is registered and sharded but lacks a `docs/linting.md` harness catalog row, leaving replay documentation incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] CI wiring for pytest and harness shards looks consistent
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that pytest requirements and shard placement for new harness targets appear consistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] `py-lint` scope excludes skill script by design
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that `make py-lint` intentionally scans only `python/`, with plot script static coverage relying on py_compile tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] Merge parity test runs redundantly
- **Reviewer(s)**: dyn-ci-parity-output.txt
- **Severity**: nit
- **Concern**: `test_merge_bash_parity.py` runs through both shard 5 and `make py-test`; reviewer marked this as redundant but harmless.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-parity-output.txt: Address the concern above.
