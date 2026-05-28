### FINDING_1: `audit-map-runs.sh` does not reject cross-skill `--log-root`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-validation-logic-output.txt
- **Severity**: important
- **Concern**: The explicit `--log-root` consistency guard is unreachable or ineffective, so `--skill design --log-root larch-logs/implement` can scan the wrong log tree instead of failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-validation-logic-output.txt: Address the concern above.

### FINDING_2: `test-rate-assertions.sh` lacks required `--skill=design` and cross-skill coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires `test-rate-assertions.sh` coverage for design token artifacts and `--plot-from` cross-skill rejection, but the harness was not extended, leaving regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: `audit-resolve-prs.sh` single-PR resolution bypasses skill title filtering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `#N` / `PR #N` resolution does not validate PR titles against the selected skill, so `--skill=design #<implement-pr>` can proceed and later map to empty or misleading run data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Repeated skill enum validation can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Multiple scripts duplicate `validate_skill` logic, increasing the chance that future enum or error-message changes diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Audit-runs skill docs still describe legacy registry and scan behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/audit-runs/SKILL.md` still documents legacy or implement-only scan registry/title behavior, which can mislead operators running design audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] `audit-map-runs.md` still hard-codes implement lookup behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-validation-logic-output.txt
- **Severity**: nit
- **Concern**: The contract documentation mentions skill-aware log roots but still describes implement-only lookup paths, creating documentation drift for design runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-validation-logic-output.txt: Address the concern above.

### FINDING_7: `audit-scan-run.md` still references legacy `scans.tsv`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The scan-run contract still refers to `scans.tsv` instead of per-skill registry files, which can send maintainers to the wrong registry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Shared audit concurrency guard blocks cross-skill audits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The 5-minute concurrency guard is keyed globally rather than per skill, so design and implement audits can block each other unless this is intentional shared locking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] `audit-scan-run.sh` does not enforce `--skill` against run directory or registry
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `--skill` is validated but not cross-checked against `--run-dir` or `--scans-tsv`, so manual or future caller mismatches can scan the wrong directory or registry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Missing resolve-prs integration coverage for skill-specific titles
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Integration tests do not cover skill-specific prior report discovery or mixed-title merged PR filtering, so bugs in `filter_prs_for_skill` or prior selection can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Missing design scan-run integration coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test invokes `audit-scan-run.sh` with `scans-design.tsv` and `--skill design`, leaving design-only scan wiring unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Report-token issue title tests do not assert skill-prefixed titles
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `gh` stub in `test-report-tokens-recompute.sh` does not require `[Implement Analysis Report]` or `[Design Analysis Report]`, so unprefixed title regressions can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Missing skill enum and missing-skill coverage across entry points
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not consistently verify missing or invalid `--skill` rejection across `run-analysis.sh` and remaining audit helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] `docs/linting.md` has stale report-token harness description
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still describes `test-report-tokens-recompute` as implement-only and omits `--skill`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] `run-analysis.sh --plot-from` does not require numeric issue IDs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--plot-from` only checks non-empty input before calling `gh issue view`, rather than rejecting non-numeric values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Prior audit lookup can miss older skill-specific reports
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Prior-report lookup relies on the default `gh issue list` window, so many recent implement reports can hide an older design audit report and make `--skill=design since last audit` fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Empty `run_id` rows can scan the skill log root
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Failed design mapping can emit empty `run_id` rows; the orchestrator may then scan `larch-logs/$SKILL/` instead of failing clearly on an unmapped PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Design UUID matching is uppercase-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Design PR title UUID extraction only accepts `[0-9A-F-]+`, so lowercase UUIDs fail to map even if the on-disk run directory exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: `run-analysis.md` documents legacy analysis report titles
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The contract still documents unprefixed `[Analysis Report]` issue titles instead of the new Implement/Design title forms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] No defect found in `filter_prs_for_skill` pagination placement
- **Reviewer(s)**: dyn-shell-validation-logic-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports that `filter_prs_for_skill` is invoked after the pagination loop and did not identify a defect for the pagination/indent concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-validation-logic-output.txt: Address the concern above.
