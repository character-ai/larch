### FINDING_1: Double redaction before issue body trim/post
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_posting_body` applies redaction twice before trim sizing/posting, diverging from the planned single-pass contract and risking mis-sized or changed posted content if redaction becomes non-idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Golden markdown fixture is missing from the branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-surface-output.txt
- **Severity**: important
- **Concern**: The golden render test references `python/fixtures/report_tokens_implement_golden.md`, but the fixture is not committed, so clean CI/fresh clones fail with `FileNotFoundError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-surface-output.txt: Address the concern above.

### FINDING_3: Token bucket schema logic is duplicated between scan and cost
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Per-vendor bucket key lists and token aggregation are duplicated across scan and cost modules, creating drift risk where one path accepts data the other prices incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Workflow grouping logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Skill/workflow grouping is copy-pasted in render and plot paths, so future workflow behavior changes can diverge between tables and charts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Duplicate env flag helpers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `env_flag_enabled` helpers are duplicated in CLI and plot code, risking inconsistent truthy-value handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Limit env var bypasses config constant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Scan reads `LARCH_REPORT_TOKENS_LIMIT` as a raw string instead of using `config.ENV_LARCH_REPORT_TOKENS_LIMIT`, weakening rename/refactor safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: `SectionPriority.BANNER` is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `SectionPriority.BANNER` exists but no banner section uses it; trim notices are inline strings, so the enum implies a contract the render pipeline does not implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Empty manifest/report warnings are misleading
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Empty manifest/report objects reuse missing-field warnings, causing operators to misdiagnose empty JSON as a missing `issue_number` or missing tokens condition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.

### FINDING_9: `--no-plot` message is emitted twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Both CLI and plot paths emit no-plot messaging, creating minor noisy duplicate output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Vendor token table can display zero/partial tokens while costs use buckets
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Rendered vendor token columns use `totals.total` while cost pricing uses bucket inputs, so reports with non-zero buckets and zero/partial totals can show misleading token counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Legacy Claude `cache_create` bucket data is ignored in bucket mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Legacy `BUCKETS_claude.cache_create` is omitted from bucket numeric checks and token-cost argv construction, so older reports with only that field can be skipped or underpriced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Limit counts directories instead of parseable runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: `LARCH_REPORT_TOKENS_LIMIT` is consumed by every run directory, including empty/invalid ones, so a limit can stop scanning before later valid runs are parsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.

### FINDING_13: Markdown table cells do not neutralize link syntax
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Untrusted `step` strings from committed token reports can flow into public GitHub issue tables as clickable Markdown links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: `token-cost.sh` stderr is forwarded without redaction/noise control
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Child stderr from `token-cost.sh` is forwarded directly, which can leak sensitive-adjacent diagnostics and flood output even on successful runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: SECURITY.md lacks the report-tokens public-issue trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security documentation does not describe which untrusted report-token fields can reach public GitHub issues, nor the redact/trim/fail-closed/non-billing model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: CLI prints full analysis before issue-post failure is known
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The CLI emits a complete report to stdout before optional GitHub issue posting, so scripts or operators may treat captured stdout as success even if the later post fails and the process exits non-zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Missing log root produces an undiagnostic empty scan
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If the skill-specific `larch-logs` directory is absent, scan exits with “No parseable token reports found” but no warning that the log root itself was missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: docs/skills.md still says `/report-tokens` has no arguments
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `docs/skills.md` lists Arguments as `(none)` even though `/report-tokens` requires `--skill` and documents optional flags, so operators may invoke it incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: Claude blended aggregate double-counts cache-create tokens
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: `_aggregate_tokens()` can sum legacy `cache_create` together with split `cache_create_5m`/`cache_create_1h`, inflating Claude blended/fallback costs on reports where legacy aggregate already equals the split sum.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### FINDING_20: Codex/Cursor blended and fallback cost aggregation undercounts cached volume
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: Blended/fallback aggregation for Codex and Cursor uses partial vendor component sums instead of bucket totals or vendor `total`, so reports where cached volume lives only in `BUCKETS_*` can be severely underpriced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### FINDING_21: Quiet-mode harness does not cover post-restore Python failures
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: latent
- **Concern**: The quiet-mode test covers happy path and pre-Python validation errors, but not failures after stdout/stderr restoration, leaving the main Python diagnostic regression only partially guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.

### FINDING_22: Operator-facing stdout is not redacted
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: important
- **Concern**: The GitHub issue body is redacted, but stdout prints rendered markdown, cache paths, and plot paths without redaction, allowing token-shaped or path-like material from run logs to leak into terminals/CI logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### FINDING_23: `gh repo view` failure diagnostics are unredacted
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Repo-resolution errors print raw `gh` stdout/stderr, unlike issue-posting errors, and may expose sensitive fragments on stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### FINDING_24: Design workflow fallback does not match bash fail-closed HARD behavior
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: important
- **Concern**: `_workflow_from` returns `unknown` for missing/invalid design classification instead of defaulting to `HARD` like the old bash helper, so older/partial design runs can be dropped from design trends and plots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.

### FINDING_25: Plot subprocess smoke test bypasses production isolation contract
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: The optional real-subprocess plot smoke test runs the child directly without `MPLCONFIGDIR` isolation and does not assert returned PNG paths survive after subprocess exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_26: Plot producer/consumer JSON contract lacks shared fixtures
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Producer and consumer tests use separate inline plot payloads, so `_series()` and `_validate_series()` can drift while both test suites still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_27: relevant-checks does not route `scripts/token-cost.sh` edits to pricing tests
- **Reviewer(s)**: dyn-ci-surface-output.txt
- **Severity**: important
- **Concern**: Changes to the pricing authority `scripts/token-cost.sh` can pass scoped `relevant-checks` without running Python pricing integration tests or report-token harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-surface-output.txt: Address the concern above.

### FINDING_28: relevant-checks does not route Python fixture-only edits to py-test
- **Reviewer(s)**: dyn-ci-surface-output.txt
- **Severity**: latent
- **Concern**: Edits under `python/fixtures/**` do not match the current Python routing glob, so golden fixture updates alone may skip `py-test`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-surface-output.txt: Address the concern above.

### OOS_1: Plot date axis differs from per-day table date basis
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt, dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Plot series use `closed_at` while per-day tables use `started_at`, so long-running issues can disagree; reviewers noted this is pre-existing/plan-documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt, dyn-scan-pipeline-output.txt: Address the concern above.

### OOS_2: Report-token temp directories are intentionally retained
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Repeated local runs accumulate `larch-report-tokens` temp directories, but this was noted as intentional for cache JSON and PNG lifetime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_3: Per-bucket happy path appears correct
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that successful per-vendor mixed bucket argv construction, KV parsing, and rate forwarding align with existing expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### OOS_4: Quiet wrapper restores stderr before Python
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that the wrapper’s `exec 1>&3 2>&4` before Python correctly fixes a prior quiet-mode FD gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.

### OOS_5: Quiet-mode stderr conventions otherwise match contract
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that pre-restore bash errors and post-restore Python stderr diagnostics follow the quiet-mode contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.

### OOS_6: Issue success output follows analysis block
- **Reviewer(s)**: dyn-quiet-fd-output.txt
- **Severity**: latent
- **Concern**: Reviewer noted that successful issue posting emits the issue URL after the analysis block, while callers must still check exit codes for late failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-quiet-fd-output.txt: Address the concern above.

### OOS_7: Issue-posting pipeline is materially improved
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed improvements including removal of raw JSON issue appendix, post-redaction trim sizing, loud failure on oversize/gh errors, slug validation, and tmpdir scrubbing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### OOS_8: Synthesized issue URLs are not verified against repository state
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Issue URLs are built from `repo_slug` and issue number without verifying the issue exists in that repository, so wrong repo configuration can produce misleading links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### OOS_9: Phase step strings still flow into posted markdown
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Phase-breakdown `step` strings still reach posted markdown tables after secret-pattern redaction; reviewer marked this as pre-existing and reduced by dropping raw JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### OOS_10: Plot subprocess stderr is unredacted
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Plot child failures echo subprocess stderr without redaction, adjacent to but outside the issue-create path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### OOS_11: Local cache NDJSON contains unredacted manifest titles
- **Reviewer(s)**: dyn-issue-body-output.txt
- **Severity**: latent
- **Concern**: Local cache NDJSON can include unredacted manifest titles and its path is echoed via the `Cache JSON:` trailer, though it is not posted to GitHub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-issue-body-output.txt: Address the concern above.

### OOS_12: Duplicate issue numbers are still aggregated
- **Reviewer(s)**: dyn-scan-pipeline-output.txt
- **Severity**: latent
- **Concern**: Multiple run directories with the same `issue_number` are aggregated without deduplication; reviewer noted this is plan-documented and matches old behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scan-pipeline-output.txt: Address the concern above.

### OOS_13: `LARCH_REPORT_TOKENS_NO_OPEN` truthiness differs from no-plot flag parsing
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: `NO_OPEN` uses raw environment truthiness while `NO_PLOT` uses flag parsing, so values like `0`/`false` behave differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### OOS_14: Matplotlib isolation appears sound
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that runtime Python remains stdlib-only, matplotlib imports are isolated to the child script, child failures degrade cleanly, and returned paths are constrained to the persistent plot temp dir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### OOS_15: `test-merge-parity` lacks a secondary `.PHONY` entry
- **Reviewer(s)**: dyn-ci-surface-output.txt
- **Severity**: nit
- **Concern**: `test-merge-parity` is wired into harness execution but absent from the secondary `.PHONY` block; reviewer marked this as Make hygiene, not a CI functional break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-surface-output.txt: Address the concern above.

### OOS_16: pytest is installed on all harness shards
- **Reviewer(s)**: dyn-ci-surface-output.txt
- **Severity**: nit
- **Concern**: Installing `pytest==9.0.3` on every harness shard adds pip work to unrelated shards; reviewer called this an acceptable trade-off, not a report-tokens correctness defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-surface-output.txt: Address the concern above.
