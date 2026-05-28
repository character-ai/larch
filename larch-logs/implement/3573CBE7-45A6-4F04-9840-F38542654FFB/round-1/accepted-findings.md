### FINDING_1: `audit-map-runs.sh` does not reject cross-skill `--log-root`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-validation-logic-output.txt
- **Severity**: important
- **Concern**: The explicit `--log-root` consistency guard is unreachable or ineffective, so `--skill design --log-root larch-logs/implement` can scan the wrong log tree instead of failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-validation-logic-output.txt: Address the concern above.


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


### FINDING_19: `run-analysis.md` documents legacy analysis report titles
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The contract still documents unprefixed `[Analysis Report]` issue titles instead of the new Implement/Design title forms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_5: Audit-runs skill docs still describe legacy registry and scan behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/audit-runs/SKILL.md` still documents legacy or implement-only scan registry/title behavior, which can mislead operators running design audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: `audit-scan-run.md` still references legacy `scans.tsv`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The scan-run contract still refers to `scans.tsv` instead of per-skill registry files, which can send maintainers to the wrong registry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


