### FINDING_1: Temp directory cleanup trap gaps can leak harness directories
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-read-design-review-budget-invoke.sh` creates temp directories before extending the active `EXIT` trap. The new `fakebin_pyonly` setup creates a leak window after `fakebin`, and the later invoke-test setup creates four directories before updating cleanup. Under `set -e`, a failed later `mktemp -d` can orphan earlier directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_5: Dedup-sweep prose has no regression check
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/approval-gates.md` adds prose-only dedup-sweep instructions and canonical breadcrumb text, but no automated check ensures the three Gate B insertions remain present. A future edit could remove or rewrite the instruction without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Missing review-plan test path can collide with stale temp files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-read-design-review-budget-invoke.sh:29` constructs `missing_rp` with `${RANDOM}`. A stale file with the same name in `$TMPDIR` could make the missing-file assertion exercise the file-parse path instead of the unreadable early-return path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Pre-existing two-directory trap gap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-read-design-review-budget-invoke.sh:47-63` already had a pre-existing two-directory cleanup trap gap for `dt` and `full_dt`; the in-scope version is the amplified four-directory gap captured above.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
