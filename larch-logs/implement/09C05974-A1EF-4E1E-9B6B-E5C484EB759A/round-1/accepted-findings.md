### FINDING_2: jq-path test can pass through the python3 branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-read-design-review-budget-invoke.sh:63-70` prepends the real `jq` directory before the fake python-only directory. On systems where `jq` and `python3` are co-located, `read-design-review-budget.sh` finds real `python3` first, so the test passes while exercising the python branch instead of the jq fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: Branch diff includes out-of-scope harness changes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The #2730 plan says no scripts, validators, lint rules, harnesses, or `.tsv` registries change, but the diff modifies `skills/design/scripts/test-read-design-review-budget-invoke.sh` and its sibling doc. Reviewers attribute those changes to issue #2715, which muddies provenance if merged under the dedup-sweep PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: CHANGELOG entry documents the wrong feature
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `CHANGELOG.md:23-29` describes the #2715 harness expansion rather than the #2730 Gate B dedup-sweep behavior, leaving the primary behavior change without a version-anchored changelog record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


