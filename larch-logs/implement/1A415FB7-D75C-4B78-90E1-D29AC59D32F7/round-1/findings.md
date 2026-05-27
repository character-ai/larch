### FINDING_1: Missing Makefile recipe for waterfall harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-revise-plan-with-waterfall` is registered in `.PHONY` and `test-harnesses-9` but has no Makefile recipe, so direct or shard-level test targets fail or skip the new harness instead of running `scripts/test-revise-plan-with-waterfall.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Unnecessary tier status helper indirection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `set_tier_status` / `get_tier_status` indirection makes waterfall tier state harder to trace while debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Whole-file reads use sed instead of cat
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `compose_prompt` uses `sed -n` for whole-file reads, which is less direct than `cat` and inconsistent with nearby bash style.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Harness bypasses production design-driver stdin path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The test harness calls or stubs `emit-plan.sh` directly instead of exercising the production `design-driver.sh` `ACTION=EMIT_PLAN` stdin contract, so stdin regressions in the real driver could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Unrelated commits mixed into feature branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The branch appears to include unrelated commits or churn outside the Piece 4 waterfall feature, increasing review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_9: Test override environment variables can select arbitrary executables
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_TEST_*` environment variables choose launcher or driver executables without a production guard, so attacker-controlled environment in a production session could run arbitrary binaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] emit-plan shares plan.txt symlink-follow behavior
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `emit-plan.sh` appears to have the same final-component `plan.txt` symlink redirect risk, independent of the current branch’s `revise-plan` changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
