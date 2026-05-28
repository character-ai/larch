### FINDING_1: duplicated --skill validators
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Seven near-identical `--skill` enum validators across audit-runs and report-tokens create drift risk for allowed values and diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: duplicated audit PR title matching
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Chore/audit PR title regex logic is duplicated across jq, grep, resolve, and map paths, requiring coordinated edits for title contract changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: stale audit title contract examples
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `audit-title.md` still documents legacy `[Run Logs Audit]` examples instead of skill-specific Implement/Design Run Logs Audit prefixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: stale audit map contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `audit-map-runs.md` still describes implement-only `larch-logs/implement` mapping and omits the design title/path behavior and `larch-logs/$SKILL` default root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: implement PR resolution now filters out normal feature PRs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-implement-branch-parity-output.txt
- **Severity**: important
- **Concern**: `audit-resolve-prs.sh` applies flush-run title filtering to `--skill=implement` paths, causing `last N`, `since last audit`, `since <ISO>`, and `#N` resolution to miss or reject normal merged implement feature PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-implement-branch-parity-output.txt: Address the concern above.

### FINDING_6: SKILL scan table omits design L1 caveat
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The audit-runs SKILL scan table presents the full implement baseline without explaining that design currently uses `scans-design.tsv` plus synthetic category-stats/cross-cutting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: registry drift diagnostic names wrong scans file
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `audit-scan-run.sh` drift diagnostics still reference `scans.tsv` instead of the active skill registry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: title matcher consumer doc lists non-consumer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `audit-title-matcher.md` lists `audit-preflight` as a consumer even though preflight does not source the matcher.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: design run IDs are not normalized consistently
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Design PR title parsing allows lowercase UUID hex and preserves casing, which can diverge from uppercase log directory names and conflicts with the plan’s uppercase-only documented contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: missing test for implement-prefixed prior audit discovery
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Test 19 only covers legacy prior audit titles for implement, so new `[Implement Run Logs Audit ...]` prior discovery could regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: missing design close-priors isolation test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Close-priors tests do not verify that design audits close only design audit issues and leave implement audit reports open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: --skill validation coverage incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Missing/invalid `--skill` tests only cover `audit-resolve-prs.sh`, leaving other audit entrypoint validators untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: missing positive design --plot-from test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run-analysis.sh --skill design --plot-from` lacks a positive test for `[Design Analysis Report]` titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: missing design skip-warning harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness verifies the design-run missing `token-report-final.json` skip-with-warning path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: duplicate test label
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Duplicate hermetic label `[69g]` makes failure output ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: jq parse failures are swallowed in close-priors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `audit-close-priors.sh` can treat a jq parse failure after successful `gh list` as an empty issue list and exit 0, leaving prior audit reports open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: explicit log-root can bypass skill consistency
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: An explicit `--log-root` outside `larch-logs/{design,implement}` can skip skill consistency checks and produce empty or misleading mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: audit-resolve contract omits implement title semantics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `audit-resolve-prs.md` does not document the intended implement title-filter behavior after restoring implement parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: report-token design fixture cleanup gap
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: important
- **Concern**: `test-report-tokens-recompute.sh` creates a design fixture under the real `larch-logs/design` tree but the `EXIT` cleanup does not remove it, so failures can leave a live-looking design run that contaminates report-token output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] unused preflight --skill parameter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `audit-preflight.sh` validates `--skill` but does not use it beyond enum checking; behavior matches the shared-lock plan but the API may confuse readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] committed run logs may contain session-derived content
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Committed implement run logs may contain session-derived content, but this is intentional per `docs/run-logs.md` and not introduced by the `--skill` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] shared audit concurrency guard
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The audit preflight concurrency guard remains label-wide across skills, so design and implement audits block each other unless `--allow-concurrent` is used.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] design registry is intentionally incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scans-design.tsv` currently contains only cache-freshness, so design audits under-report other categories until follow-up adapters land.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] rate assertions design fixture residual risk
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: nit
- **Concern**: `test-rate-assertions.sh` also uses an in-tree design fixture but includes it in the `EXIT` trap, leaving only residual abnormal-termination cleanup risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] implement fixture predates branch
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: nit
- **Concern**: The implement fixture in `test-report-tokens-recompute.sh` predates this branch and is already covered by cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] report-token harnesses use in-tree fixtures
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: nit
- **Concern**: Report-token harnesses intentionally write fixtures under `$REPO/larch-logs/{implement,design}`, unlike audit harnesses that use `${TMPDIR}`, increasing cross-talk risk when cleanup is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] implement map path parity observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: Implement `audit-map-runs.sh` default and explicit `larch-logs/implement` paths remain consistent with the implement branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] implement report-token parity observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: Implement `run-analysis.sh` still reads implement token/timing reports and validates legacy or new implement analysis report titles for `--plot-from`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] audit-scan-run root guard observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: The new guard rejecting a skill log root as `--run-dir` is additive safety rather than an implement parity regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] audit-close-priors skill scoping observation
- **Reviewer(s)**: dyn-implement-branch-parity-output.txt
- **Severity**: nit
- **Concern**: Skill-scoped title matching in `audit-close-priors.sh` is an intentional multi-skill behavior change rather than an implement-path regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-implement-branch-parity-output.txt: Address the concern above.
