### FINDING_1: Quiet wrapper harness is not wired into CI/Makefile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ci-harness-output.txt
- **Severity**: important
- **Concern**: `skills/report-tokens/scripts/test-run-analysis-quiet.sh` exists as the quiet/FD-restore regression harness, but is not registered in Makefile, CI harness shards, or relevant-checks, so quiet-mode stream restoration can regress without automated signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ci-harness-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Successful issue creation no longer prints the created issue URL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt
- **Severity**: important
- **Concern**: The Python `/report-tokens` issue-post success path exits successfully but no longer prints the `gh issue create` URL / prior “Analysis report issue created” confirmation, breaking operator visibility and stdout-scraping automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Planned fake-Runner CLI e2e stdout coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt
- **Severity**: important
- **Concern**: CLI orchestration tests only cover narrow argv/env behavior; the planned fake-Runner end-to-end test asserting stdout contracts such as the analysis header and `Cache JSON:` line is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt: Address the concern above.

### FINDING_4: Workflow resolution omits bash fallback chain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `report_tokens_scan.py` inlines workflow resolution and may miss workflow locations handled by the bash helper fallback chain, skewing classification for design SIMPLE/HARD plots and tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Invalid `LARCH_REPORT_TOKENS_REPO` values are not fail-closed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cli-wrapper-output.txt
- **Severity**: important
- **Concern**: Malformed or unsafe `LARCH_REPORT_TOKENS_REPO` overrides are silently ignored or loosely accepted, producing late generic failures or misleading rendered links instead of an explicit owner/repo validation error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cli-wrapper-output.txt: Address the concern above.

### FINDING_6: Duplicate helper functions are spread across report-tokens modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_as_mapping` / `_date` style helpers are duplicated across scan, cost, render, and plot modules, increasing maintenance risk for JSON-shape changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: `SectionPriority.BANNER` is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The banner priority enum value is not represented as a `ReportSection`, making trim/banner immutability harder to reason about or test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Truncation notice uses internal section keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Trimmed issue bodies report omitted internal keys like `trends,rates` instead of reader-facing markdown section titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Pricing provenance and underpricing sanity are not surfaced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-token-pricing-output.txt
- **Severity**: latent
- **Concern**: Rendered output does not surface fallback pricing provenance or cross-check token totals against zero/underpriced vendor costs, so misleading totals can appear authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-token-pricing-output.txt: Address the concern above.

### FINDING_10: `NO_PLOT=0` disables plots inconsistently
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `report_tokens_plot.plot()` reads raw `LARCH_REPORT_TOKENS_NO_PLOT`, so `0` disables plotting even though CLI env parsing treats `0` as false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Bucket-mode token pricing can under-report spend
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: Bucket pricing is selected for non-empty or malformed `BUCKETS_*` objects even when the actual priced lanes are zero, causing `token-cost.sh` to return zero cost despite positive aggregate vendor totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-token-pricing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Real `scripts/token-cost.sh` integration coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: Tests use fake Runner output instead of invoking the real `scripts/token-cost.sh`, so argv/env/KV contract drift can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-pricing-output.txt: Address the concern above.

### FINDING_13: Issue trimming measures a different body than `gh issue create` posts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt
- **Severity**: important
- **Concern**: `post_issue()` / `_trim_sections()` trim after one redaction pass, but `gh.issue_create()` applies fail-closed redaction again, so a body can pass byte trimming yet fail posting at the edge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt: Address the concern above.

### FINDING_14: Scan follows symlinked run directories outside `larch-logs`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Symlinked run directories under `larch-logs` can point outside the repo and cause external JSON to be read into public aggregates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Plot parent trusts child-returned paths
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: `report_tokens_plot.py` trusts plot child JSON paths without confirming they are existing files confined to `plot_dir`, which can print bogus paths or invoke macOS `open` on unintended files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Stdout exposes unredacted cache/temp paths
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-issue-publish-output.txt
- **Severity**: nit
- **Concern**: CLI stdout includes full analysis text such as `Cache JSON:` temp paths, while only the GitHub issue body is redacted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-issue-publish-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Report-tokens trust boundary is undocumented in `SECURITY.md`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` does not document that `larch-logs` are untrusted or which report-token fields may reach public GitHub issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Phase 7 Python ship driver needs separate security review
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The Python `ship-pr` driver expands runtime attack surface but was not reviewed in the report-tokens-focused review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: `unknown/unknown` issue URLs are fabricated when repo slug resolution fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ship-parity-output.txt
- **Severity**: important
- **Concern**: When repo slug resolution fails, especially with `--no-issue` or before issue-post failure, rendered tables can contain plausible but false `https://github.com/unknown/unknown/issues/N` links.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt, dyn-ship-parity-output.txt: Address the concern above.

### FINDING_20: Git repo-root resolution failure falls back to cwd
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ship-parity-output.txt
- **Severity**: important
- **Concern**: If `git rev-parse` fails, scanning falls back to `Path.cwd()` with only a warning, which can scan the wrong `larch-logs` tree or exit 0 with empty analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-ship-parity-output.txt: Address the concern above.

### FINDING_21: Planned issue trim/oversize tests are missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-publish-output.txt
- **Severity**: important
- **Concern**: Tests do not cover body trimming, truncation banner/order, oversize-after-trim failure, or fail-closed `ShipError` propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-issue-publish-output.txt: Address the concern above.

### FINDING_22: Empty manifest objects are skipped without warning
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Runs with `{}` manifests disappear silently instead of emitting a clear skip warning for missing `issue_number`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Partial-success stdout semantics after issue-post failure are unclear
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt, dyn-cli-wrapper-output.txt
- **Severity**: nit
- **Concern**: The CLI prints analysis to stdout before issue posting, then may fail non-zero, creating partial-success behavior that needs explicit documentation or stderr signaling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt, dyn-cli-wrapper-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `LIMIT` counts directories rather than unique issues
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Duplicate issue directories can double-count costs because limiting/deduplication is directory-based rather than issue-number-based.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] Plot and table date axes differ
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Plots bucket by `closed_at` while render tables use `started_at`, so trend charts and per-day tables can disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Temp plot/cache roots are retained
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Temporary plot/cache directories are not cleaned up automatically, so repeated runs can accumulate files under `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_27: Scan fail-soft fixture coverage is incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned tests for bad manifest, timing, token-report, and slug-missing scan cases are absent, so fail-soft behavior may regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_28: Design SIMPLE/HARD render split lacks golden coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Render tests do not assert separate SIMPLE and HARD per-workflow trend sections for design runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Phase 7 / run-log commits add branch noise
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-ship-parity-output.txt
- **Severity**: latent
- **Concern**: Unrelated Phase 7 / telemetry commits on the same branch make the report-tokens work harder to review in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-ship-parity-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Bucket underpricing may be legacy parity rather than new regression
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: nit
- **Concern**: The all-bucket-object legacy bash path appears to have had a similar zero-lane pricing weakness, so part of the bucket issue may not be newly introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### FINDING_31: Empty-record analysis skips requested issue posting
- **Reviewer(s)**: dyn-cli-wrapper-output.txt
- **Severity**: important
- **Concern**: When scan finds zero parseable runs, the CLI returns success after printing “No parseable token reports found” and does not create an issue even if issue posting was requested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-wrapper-output.txt: Address the concern above.

### FINDING_32: Repo/post failures changed exit code from 1 to 4
- **Reviewer(s)**: dyn-cli-wrapper-output.txt
- **Severity**: latent
- **Concern**: Repo-resolution and issue-posting failures now return `EXIT_BAIL` 4 instead of the prior operator-error exit 1, which can break callers that classify failures by code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-wrapper-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Wrapper does not validate Python version
- **Reviewer(s)**: dyn-cli-wrapper-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh` checks only for `python3`, not the documented Python >=3.12 requirement, producing less clear runtime failures on older interpreters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-wrapper-output.txt: Address the concern above.

### FINDING_34: Plot child does not validate the version/skill/series contract
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: `plot-cost-over-time.py` accepts malformed or drifted plot input without enforcing `version`, allowed `skill`, required labels, or expected series cardinality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_35: Plot child silently skips malformed series/points
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Invalid `series` or `points` entries are skipped with `continue`, letting partially invalid payloads exit 0 and appear equivalent to valid “no data” runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Plot smoke test omits design/MPLCONFIGDIR coverage
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: The plot smoke test covers only an implement payload and does not set `MPLCONFIGDIR`, unlike production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Stdlib-only plot isolation invariant appears satisfied
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: Matplotlib remains isolated to the child script and the core Python modules remain stdlib-only; this is an out-of-scope positive observation rather than a defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.

### FINDING_38: Python ship path lacks authoritative phase state for routing/retries
- **Reviewer(s)**: dyn-ship-parity-output.txt
- **Severity**: important
- **Concern**: Phase 7 Python ship output does not provide or update phase state consistently with orchestrator instructions, so agents can read stale `PHASE` values, re-enter bash shipping, or mis-bucket Exit 6 retry counters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-parity-output.txt: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] Foreground ship invoke block still shows only bash path
- **Reviewer(s)**: dyn-ship-parity-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md` documents the Python selector in prose but the foreground Invoke block still shows `ship-pr.sh`, making Python cutover behavior easy to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-parity-output.txt: Address the concern above.

### FINDING_40: `test-merge-parity` pytest entrypoint differs from `py-test`
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: latent
- **Concern**: `test-merge-parity` runs pytest from repo root while `py-test` runs from `python/`, so CI gates can diverge on import/config discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

### FINDING_41: Quiet harness git shim hardcodes `/usr/bin/git`
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: latent
- **Concern**: The quiet harness falls back to `/usr/bin/git`, reducing portability once the harness is added to CI or local matrices.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] `docs/linting.md` names the wrong harness requirements file
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: Docs still say the harness matrix installs from `requirements-lint.txt` even though CI uses `.github/workflows/requirements-test-harnesses.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] Report-tokens Python coverage is correctly gated through `py-test`
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: Existing report-tokens Python coverage appears appropriately gated through `make py-test` / `python-tests`; this is an out-of-scope positive observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] Harness pytest dependency addition is appropriate
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: Adding `pytest==9.0.3` to harness workflow requirements matches Python test requirements and needs no shard-count change; this is an out-of-scope positive observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.
