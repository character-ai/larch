### FINDING_1: Duplicate skill validation logic can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Six audit entrypoints plus `run-analysis.sh` each define equivalent skill-validation case blocks. If allowed values or error text changes in only one path, one CLI can accept or reject the wrong skill while other tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Design PR title matching is duplicated and inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Design PR title matching/parsing is duplicated across jq, grep, sed, resolve, and map paths, and the current filter accepts lowercase hex despite the plan/acceptance requiring uppercase UUID segments. A title-format change or regex mismatch can make design audits include the wrong PRs or fail to map `RUN_ID` consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Design scan documentation overstates registry coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Documentation implies the full implement scan suite applies to design audits, but the design registry only registers cache-freshness. Operators may run `/audit-runs --skill design` expecting EXON/OOS or full implement-style scans and misread the narrower report as a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: scan-run skill behavior is under-documented
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `--skill` in `audit-scan-run.sh` is validated but primarily selects the scan registry path; behavior is driven by the TSV registry. Without documentation, future contributors may add duplicated skill branches in the scanner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Unknown title-matcher skill is indistinguishable from a non-match
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `audit-title-matcher.sh` returns `1` for an unknown `--skill`, the same as a valid skill with a non-matching title. A caller typo can be treated as “no prior audit report” instead of invalid input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Prior audit test coverage misses new implement title prefix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Test 45 only verifies closing the legacy implement audit title. A regression that stopped matching `[Implement Run Logs Audit …]` prior issues could pass CI while leaving new-prefix priors open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Design timing smoke uses the wrong fixture shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The design smoke in `test-rate-assertions.sh` uses `token-report.json` as `timing-report-final.json`, so regressions in design timing or `workflow_path` reads from the real timing report could pass undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Missing-token design log skip path lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-report-tokens-recompute.sh` has no targeted regression for a design run with a manifest but no `token-report-final.json`. That path could stop skipping cleanly or crash without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Design since-last-audit lacks cross-skill prior coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover `--skill design` since-last-audit when only implement audit reports exist. If title filtering regresses, design audits could incorrectly select an implement prior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Probe stderr files can dirty the repo root
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-report-tokens-recompute.sh` writes probe stderr files under the repository root, so an interrupted harness can leave `.tmp-report-tokens-*.err` files in the worktree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: since-last-audit over-fetches issue bodies before skill filtering
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `audit-resolve-prs.sh` lists up to 100k audit-report issues with full bodies before applying the skill title filter. Large audit-report histories can cause excessive GitHub payload size, memory use, and local runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: close-priors over-fetches open audit issues
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `audit-close-priors.sh` bulk-lists up to 100k open audit-report issues before filtering by skill title, inflating API traffic and runtime when few issues actually match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: since-last-audit conflates GitHub failures with no matching prior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `since-last-audit` reports the same no-prior message when GitHub listing fails and when prior audit reports exist only for other skills. Operators cannot distinguish expired auth or API failure from a valid “no matching design prior” state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: run-dir is not constrained to the selected skill log root
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `audit-scan-run.sh` validates `--run-dir` only by basename/root shape, not that it lives under `larch-logs/$SKILL`. A run from another skill can be scanned with the wrong registry and produce misleading NDJSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: jq filter failures are misreported as GitHub API failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In `audit-resolve-prs.sh`, malformed merged-PR JSON or jq filter bugs are reported as `gh api failed listing merged PRs`, sending operators toward network/auth debugging instead of parse/filter debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Design category-stats emits partial_data for an intentionally missing artifact
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Design runs always emit a category-stats `partial_data` anomaly for missing `review-findings-full.jsonl`, even though design runs intentionally omit that artifact. Reports therefore show a misleading anomaly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: SKILL noise-exclusion duplicates title-matcher regex
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The proposal noise-exclusion logic in `SKILL.md` duplicates the audit title regex instead of calling `audit-title-matcher.sh`. Future title-shape changes can update the matcher while leaving orchestrator/test filtering stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: audit-preflight is listed as a title-matcher consumer but does not use it
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `audit-preflight.sh` neither sources nor calls `audit-title-matcher.sh` even though acceptance criteria and the plan list preflight as a consumer. Prior-report title discrimination is only implemented in resolve/close, so the documented preflight behavior is overstated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Shared audit-report concurrency lock blocks cross-skill audits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The audit-report concurrency lock is shared across skills, so back-to-back or parallel design and implement audits can block each other unless `--allow-concurrent` is used. Sources mark this as out of scope because it appears plan-intended or pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] report-tokens docs omit required skill argument
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` omits the required `--skill` argument for the report-tokens smoke command, so operators following the docs hit an immediate `run-analysis.sh` usage failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Empty skill logs produce empty analysis without hard failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Missing or empty `larch-logs/$SKILL` yields an empty analysis rather than a hard failure. The reviewer identifies this as inherited implement behavior and out of scope unless empty-skill scans should fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
