### FINDING_12: [OUT_OF_SCOPE] Real `scripts/token-cost.sh` integration coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-pricing-output.txt
- **Severity**: important
- **Concern**: Tests use fake Runner output instead of invoking the real `scripts/token-cost.sh`, so argv/env/KV contract drift can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-pricing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] Stdout exposes unredacted cache/temp paths
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-issue-publish-output.txt
- **Severity**: nit
- **Concern**: CLI stdout includes full analysis text such as `Cache JSON:` temp paths, while only the GitHub issue body is redacted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-issue-publish-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Report-tokens trust boundary is undocumented in `SECURITY.md`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` does not document that `larch-logs` are untrusted or which report-token fields may reach public GitHub issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Phase 7 Python ship driver needs separate security review
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The Python `ship-pr` driver expands runtime attack surface but was not reviewed in the report-tokens-focused review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] Successful issue creation no longer prints the created issue URL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt
- **Severity**: important
- **Concern**: The Python `/report-tokens` issue-post success path exits successfully but no longer prints the `gh issue create` URL / prior “Analysis report issue created” confirmation, breaking operator visibility and stdout-scraping automation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Partial-success stdout semantics after issue-post failure are unclear
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt, dyn-cli-wrapper-output.txt
- **Severity**: nit
- **Concern**: The CLI prints analysis to stdout before issue posting, then may fail non-zero, creating partial-success behavior that needs explicit documentation or stderr signaling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-issue-publish-output.txt, dyn-cli-wrapper-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] `LIMIT` counts directories rather than unique issues
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Duplicate issue directories can double-count costs because limiting/deduplication is directory-based rather than issue-number-based.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] Plot and table date axes differ
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-plot-isolation-output.txt
- **Severity**: latent
- **Concern**: Plots bucket by `closed_at` while render tables use `started_at`, so trend charts and per-day tables can disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] Temp plot/cache roots are retained
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Temporary plot/cache directories are not cleaned up automatically, so repeated runs can accumulate files under `/tmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] Phase 7 / run-log commits add branch noise
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-ship-parity-output.txt
- **Severity**: latent
- **Concern**: Unrelated Phase 7 / telemetry commits on the same branch make the report-tokens work harder to review in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-ship-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] Planned fake-Runner CLI e2e stdout coverage is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt
- **Severity**: important
- **Concern**: CLI orchestration tests only cover narrow argv/env behavior; the planned fake-Runner end-to-end test asserting stdout contracts such as the analysis header and `Cache JSON:` line is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cli-wrapper-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] Bucket underpricing may be legacy parity rather than new regression
- **Reviewer(s)**: dyn-token-pricing-output.txt
- **Severity**: nit
- **Concern**: The all-bucket-object legacy bash path appears to have had a similar zero-lane pricing weakness, so part of the bucket issue may not be newly introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-pricing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] Wrapper does not validate Python version
- **Reviewer(s)**: dyn-cli-wrapper-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh` checks only for `python3`, not the documented Python >=3.12 requirement, producing less clear runtime failures on older interpreters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-wrapper-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_36: [OUT_OF_SCOPE] Plot smoke test omits design/MPLCONFIGDIR coverage
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: The plot smoke test covers only an implement payload and does not set `MPLCONFIGDIR`, unlike production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] Stdlib-only plot isolation invariant appears satisfied
- **Reviewer(s)**: dyn-plot-isolation-output.txt
- **Severity**: nit
- **Concern**: Matplotlib remains isolated to the child script and the core Python modules remain stdlib-only; this is an out-of-scope positive observation rather than a defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plot-isolation-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] Foreground ship invoke block still shows only bash path
- **Reviewer(s)**: dyn-ship-parity-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md` documents the Python selector in prose but the foreground Invoke block still shows `ship-pr.sh`, making Python cutover behavior easy to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_42: [OUT_OF_SCOPE] `docs/linting.md` names the wrong harness requirements file
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: Docs still say the harness matrix installs from `requirements-lint.txt` even though CI uses `.github/workflows/requirements-test-harnesses.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] Report-tokens Python coverage is correctly gated through `py-test`
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: Existing report-tokens Python coverage appears appropriately gated through `make py-test` / `python-tests`; this is an out-of-scope positive observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_44: [OUT_OF_SCOPE] Harness pytest dependency addition is appropriate
- **Reviewer(s)**: dyn-ci-harness-output.txt
- **Severity**: nit
- **Concern**: Adding `pytest==9.0.3` to harness workflow requirements matches Python test requirements and needs no shard-count change; this is an out-of-scope positive observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-harness-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] Pricing provenance and underpricing sanity are not surfaced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-token-pricing-output.txt
- **Severity**: latent
- **Concern**: Rendered output does not surface fallback pricing provenance or cross-check token totals against zero/underpriced vendor costs, so misleading totals can appear authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-token-pricing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

