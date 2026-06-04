### FINDING_1: Double redaction before issue body trim/post
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `_posting_body` applies redaction twice before trim sizing/posting, diverging from the planned single-pass contract and risking mis-sized or changed posted content if redaction becomes non-idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_13: Markdown table cells do not neutralize link syntax
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Untrusted `step` strings from committed token reports can flow into public GitHub issue tables as clickable Markdown links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_15: SECURITY.md lacks the report-tokens public-issue trust model
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Security documentation does not describe which untrusted report-token fields can reach public GitHub issues, nor the redact/trim/fail-closed/non-billing model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


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


### FINDING_2: Golden markdown fixture is missing from the branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-surface-output.txt
- **Severity**: important
- **Concern**: The golden render test references `python/fixtures/report_tokens_implement_golden.md`, but the fixture is not committed, so clean CI/fresh clones fail with `FileNotFoundError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-surface-output.txt: Address the concern above.


### FINDING_20: Codex/Cursor blended and fallback cost aggregation undercounts cached volume
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: Blended/fallback aggregation for Codex and Cursor uses partial vendor component sums instead of bucket totals or vendor `total`, so reports where cached volume lives only in `BUCKETS_*` can be severely underpriced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.


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


### FINDING_6: Limit env var bypasses config constant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Scan reads `LARCH_REPORT_TOKENS_LIMIT` as a raw string instead of using `config.ENV_LARCH_REPORT_TOKENS_LIMIT`, weakening rename/refactor safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: `--no-plot` message is emitted twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Both CLI and plot paths emit no-plot messaging, creating minor noisy duplicate output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


