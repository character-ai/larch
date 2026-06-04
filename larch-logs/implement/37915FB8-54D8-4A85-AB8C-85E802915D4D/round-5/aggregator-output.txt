### FINDING_1: Truncation banner is not modeled as a protected report section
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `SectionPriority.BANNER` is unused, and the actual truncation notice is not a `ReportSection`, so the trim contract and tests do not protect the posted notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Trim priority drops suggestions before trend tables
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Under size pressure, cost-reduction suggestions are removed while per-day trend tables remain, which conflicts with the planned trim ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicate `_as_mapping` helper can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_as_mapping` is duplicated across scan and cost modules, creating maintenance drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Inconsistent boolean env flag parsing can drift or mis-handle `NO_OPEN`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-plot-boundary-output.txt
- **Severity**: latent
- **Concern**: Boolean env parsing is duplicated/inconsistent; specifically `LARCH_REPORT_TOKENS_NO_OPEN=0` suppresses auto-open because it is checked as a raw non-empty string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-plot-boundary-output.txt: Address the concern above.

### FINDING_5: Duplicate date parsing helper can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Date parsing helpers are duplicated between render and plot code, risking silent divergence in date/axis semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Workflow grouping logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Implement/design workflow aggregation rules are duplicated, so tables and plots can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: `SectionPriority.CACHE` name is ambiguous
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `CACHE` names the rates section and may be confused with NDJSON cache paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Render layer depends on pricing/cost module rollups
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Rendering imports token aggregation from the cost layer, coupling display rendering to pricing argv construction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Test fake runner dataclasses are duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple identical fake runner dataclasses across tests make runner contract changes require repeated edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: Empty manifest/report dictionaries produce misleading warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Empty JSON objects are reported as missing/invalid fields instead of as empty manifests/reports, which can mislead operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Scan uses raw repo env var string instead of config constant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `report_tokens_scan.py` references the raw `LARCH_REPORT_TOKENS_REPO` string, so future config renames can miss this call site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Unrelated merge parity target broadens PR scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-merge-parity` appears bundled with report-tokens work, increasing PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Workflow resolution is duplicated between Bash and Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Bash and Python workflow resolution can diverge on SIMPLE/HARD classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_14: Golden markdown fixture is missing from the branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `python/fixtures/report_tokens_implement_golden.md` is absent/untracked, so fresh-clone pytest can fail with `FileNotFoundError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Plot omits runs without parseable `closed_at`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-log-scan-output.txt
- **Severity**: latent
- **Concern**: Runs can appear in printed totals/tables but disappear from PNG trends because plots use `closed_at` and silently skip missing/short values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-log-scan-output.txt: Address the concern above.

### FINDING_16: `LARCH_REPORT_TOKENS_LIMIT=0` scans everything
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A limit of `0` is treated as unlimited, contrary to an operator’s likely expectation of zero scanned directories or an explicit error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Bail and stalled exits share code 4
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `EXIT_BAIL` and `EXIT_STALLED` share an exit code, so callers cannot distinguish them by status alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_18: Plot subprocess schema tests fail when matplotlib is absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Negative plot subprocess tests expect schema exit `2`, but missing matplotlib exits `3` first, causing CI failure or masking schema regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: PNG plotting success path may never run in CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Optional plot smoke tests no-op without matplotlib, so CI may not exercise real PNG output or JSON stdout paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: Quiet wrapper lacks gh repo resolution failure coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The quiet wrapper harness does not cover gh repo resolution failure behavior, leaving quiet-mode stderr and friendly failure messaging under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_21: Only implement rendering has golden coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Design SIMPLE/HARD markdown rendering lacks equivalent golden coverage, so design regressions may pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Wrapper-level issue posting failure coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-cli-bridge-output.txt
- **Severity**: nit
- **Concern**: The quiet wrapper harness does not exercise `gh issue create` or issue-body trim hard failures under quiet-mode env vars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-cli-bridge-output.txt: Address the concern above.

### FINDING_23: Symlinked report files can expose local secrets
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The scanner skips symlinked run directories but follows symlinked JSON files inside runs, allowing malicious committed logs to read local files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_24: `token-cost.sh` stderr is forwarded unredacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Child stderr from pricing can expose tokens or sensitive paths to terminal observers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_25: Plot subprocess output is forwarded unredacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Plot child stderr/stdout details can leak local paths or sensitive output through user stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_26: JSON log reads are unbounded
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Unbounded `read_text` on log JSON files can exhaust memory, especially with huge files or symlinks to huge files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] SECURITY.md names stale redaction implementation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` references stale `redact-secrets.sh` wording instead of the current Python redaction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_28: Invalid repo override blocks offline `--no-issue` analysis
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: A stale invalid `LARCH_REPORT_TOKENS_REPO` override raises during scan even when issue posting is disabled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_29: gh repo failure emits alarming stderr despite successful `--no-issue`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: With issue posting disabled, gh repo resolution failure can still print `ERROR` while the CLI exits successfully, confusing CI that treats stderr errors as failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_30: Stdout report can differ from trimmed filed issue
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Automation may read full stdout and assume it matches the GitHub issue, while the filed issue body may have been trimmed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_31: `token-cost.sh` stderr is printed even on success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Advisory stderr from successful pricing runs can make pipelines that treat any stderr as failure flake.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_32: Cache NDJSON rows lack pricing-source metadata
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Downstream cache consumers cannot tell whether rows used `token-cost.sh` or blended fallback pricing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_33: Issue bodies are redacted twice
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Report-token issue bodies are redacted once in issue assembly and again in `gh.issue_create`, which can violate the single-pass sizing/trim contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_34: `safe_int` no longer matches legacy Bash token parsing
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: The Python `safe_int` rejects comma-formatted strings and fractional floats that the legacy helper handled, potentially changing token totals, argv mode, and costs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### FINDING_35: Suggestions text overstates `token-cost.sh` authority when fallback pricing is used
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: latent
- **Concern**: The report can claim shell pricing authority even when headline totals include Python blended fallback costs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] Mixed per-vendor bucket/blended pricing is intentional
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: nit
- **Concern**: Mixed per-vendor bucket versus blended argv can change totals versus historical reports, but was identified as an intentional plan change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Plot and table date-axis mismatch is accepted legacy behavior
- **Reviewer(s)**: dyn-token-pricing-output.txt, dyn-log-scan-output.txt
- **Severity**: nit
- **Concern**: Plots use `closed_at` while per-day tables use `started_at`; reviewers marked this as documented/preserved behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt, dyn-log-scan-output.txt: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] Design `unknown` workflow runs are omitted from SIMPLE/HARD trend and plot grouping
- **Reviewer(s)**: dyn-token-pricing-output.txt, dyn-log-scan-output.txt
- **Severity**: latent
- **Concern**: Design runs with `workflow="unknown"` are included in aggregate/headline surfaces but excluded from SIMPLE/HARD trend and plot series; one source marked this out-of-scope for pricing math.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt, dyn-log-scan-output.txt: Address the concern above.

### FINDING_39: Repo slug failure does not fail fast when issue posting is enabled
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: latent
- **Concern**: If gh repo resolution fails, the CLI still prices/renders/prints the report before exiting non-zero at the issue-posting gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.

### FINDING_40: Wrapper lacks explicit Python version prerequisite check
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh` only checks for `python3`, so older interpreters can fail later with import/runtime errors instead of a clear prerequisite message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.

### FINDING_41: Python report-token bail exits may break callers expecting old exit codes
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: latent
- **Concern**: Operational failures now propagate as exit code `4`, while the old bash entrypoint used different wrapper-side failure codes such as `1`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] Quiet wrapper restores stderr as an improvement
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: nit
- **Concern**: Restoring both stdout and stderr before Python exec is noted as an improvement over the removed bash path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] Limit counts scanned directories rather than parsed records
- **Reviewer(s)**: dyn-log-scan-output.txt
- **Severity**: nit
- **Concern**: Low `LARCH_REPORT_TOKENS_LIMIT` values can yield zero parseable runs because the limit counts scanned directories, which was called out as a known quirk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-scan-output.txt: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] Scan fail-soft behavior matches stated contracts
- **Reviewer(s)**: dyn-log-scan-output.txt
- **Severity**: nit
- **Concern**: Bad JSON, missing numeric totals, bucket gaps, repo-slug fail-soft behavior, and implement unknown workflow inclusion were identified as matching contracts except for separately noted design reconciliation concerns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-scan-output.txt: Address the concern above.

### FINDING_45: `No plots generated.` conflates opt-out with plot failure
- **Reviewer(s)**: dyn-plot-boundary-output.txt
- **Severity**: latent
- **Concern**: The CLI prints the same stdout line for disabled plotting, failed/skipped matplotlib subprocesses, and empty validated series.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-boundary-output.txt: Address the concern above.

### FINDING_46: Python merge path skips bash version-race gate
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: important
- **Concern**: With `LARCH_SHIP_PR_IMPL=python`, release-bump branches can reach `gh pr merge` without the same-version bump gate still enforced by `merge-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

### FINDING_47: `RunContext.from_env()` defaults merge to enabled
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: important
- **Concern**: Missing `MERGE` env enables merge/CI/postmerge behavior, unlike default `/implement` semantics where merge is false unless requested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

### FINDING_48: Post-merge log refresh failures are mislabeled as redaction failures
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: latent
- **Concern**: `flush_logs_post` catches all `ShipError`s and reports `redaction-failed`, including final-report write failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

### FINDING_49: `restore-finalize-state.sh` early return can leave finalize state incomplete
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: important
- **Concern**: If finalize already has `PR_NUMBER`, the script can skip merging other required keys from ship state, leaving teardown with partial state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] Report-tokens live behavior aligns with plan
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: nit
- **Concern**: The reviewer marked current report-tokens wrapper/CLI/issue behavior as aligned with the #3434 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] Bash remains the default ship-pr runtime
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: nit
- **Concern**: Python merge/run-context/finalize gaps matter when the Python driver is selected or modules are exercised directly; default runtime remains bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.

### FINDING_52: [OUT_OF_SCOPE] Parity harness lacks Python-vs-bash version-race pairing
- **Reviewer(s)**: dyn-shell-parity-output.txt
- **Severity**: latent
- **Concern**: Existing merge parity coverage does not pair Python and bash behavior for version-race or bump-subject scenarios still enforced by `merge-pr.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-parity-output.txt: Address the concern above.
