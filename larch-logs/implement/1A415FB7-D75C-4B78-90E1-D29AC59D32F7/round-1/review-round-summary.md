# Review Round 1

- Mode: `diff`
- 4 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: Missing Makefile recipe for waterfall harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-revise-plan-with-waterfall` is registered in `.PHONY` and `test-harnesses-9` but has no Makefile recipe, so direct or shard-level test targets fail or skip the new harness instead of running `scripts/test-revise-plan-with-waterfall.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: git apply --check status disagrees with plan wording
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `git apply --check` failures emit `apply-failed` / failed-apply status, while the plan step expects `invalid-patch`, which can misclassify all-check-failure rounds for callers or harnesses that distinguish validation from apply failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: restore_plan failures are masked
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `restore_plan` failures are swallowed with `|| true`, so a failed restore after partial mutation can let later tiers run against corrupted `plan.txt` and report misleading final hashes or statuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: plan.txt canonicalization does not reject final-component symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `canonical_path()` does not resolve the final `plan.txt` symlink, allowing a symlink that passes the invariant while `git apply`, `cp`, or `mv` write outside `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


