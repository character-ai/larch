# Review Round 5

- Mode: `diff`
- 23 accepted, 15 rejected (15 exonerated)

## Accepted Findings

### FINDING_10: Empty manifest/report dictionaries produce misleading warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Empty JSON objects are reported as missing/invalid fields instead of as empty manifests/reports, which can mislead operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


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


### FINDING_21: Only implement rendering has golden coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Design SIMPLE/HARD markdown rendering lacks equivalent golden coverage, so design regressions may pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


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


### FINDING_40: Wrapper lacks explicit Python version prerequisite check
- **Reviewer(s)**: dyn-cli-bridge-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh` only checks for `python3`, so older interpreters can fail later with import/runtime errors instead of a clear prerequisite message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-bridge-output.txt: Address the concern above.


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


### FINDING_6: Workflow grouping logic is duplicated between render and plot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Implement/design workflow aggregation rules are duplicated, so tables and plots can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


