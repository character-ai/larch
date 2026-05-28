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


### FINDING_19: report-token design fixture cleanup gap
- **Reviewer(s)**: dyn-test-fixture-contamination-output.txt
- **Severity**: important
- **Concern**: `test-report-tokens-recompute.sh` creates a design fixture under the real `larch-logs/design` tree but the `EXIT` cleanup does not remove it, so failures can leave a live-looking design run that contaminates report-token output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-fixture-contamination-output.txt: Address the concern above.


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


