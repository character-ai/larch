### FINDING_1: `scripts/ship-pr.md` omits `RELEVANT_CHECKS_SKIPPED` in helper success contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Prose in the sibling / Helper Contracts area still treats success as `RELEVANT_CHECKS_OK=true` only, while `ship-pr.sh` (e.g. `is_relevant_checks_clean`) treats `RELEVANT_CHECKS_SKIPPED=true` as a non-failing, clean outcome on rc=0. Readers, fork operators, or tests derived from the doc can encode OK-only predicates, stall, mis-handle skip, or miss stderr skip breadcrumbs relative to the implemented helper contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_12: `skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` does not pin `RELEVANT_CHECKS_SKIPPED=true`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Unlike the review harness, the implement anti-halt harness does not require `RELEVANT_CHECKS_SKIPPED=true` in the continuation window, so SKILL.md skip-continuation wording could regress without CI until a manual `/implement` mis-halts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---


### FINDING_2: `skills/review/references/domain-rules.md` genericity vs `scripts/` exemption conflict
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Genericity rules describe `scripts/` as generic and also as consumer-local exempt, so Step 3 reviewers may skip valid genericity findings for shared `scripts/` or mis-apply exemptions beyond true consumer-local helpers. Risk is inconsistent review application unless the exemption is scoped to explicit paths (named scripts vs blanket `scripts/`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---


### FINDING_7: Docs vs skill wording mismatch (fenced helper vs inline Step 3e)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `docs/linting.md` (and related harness doc) describe a fenced helper invocation for `/review` Step 3e while the skill uses inline prose, inviting churn or false belief that docs/harness disagree with runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---


### FINDING_8: `scripts/test-relevant-checks-helper-failure.sh` non-executable branch lacks `EXIT_CODE=126` stdout assertion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The check-script-not-executable case does not assert `EXIT_CODE=126` on stdout, so a regression could drop `EXIT_CODE` from the envelope without failing the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---


### FINDING_9: Dangling / broken `scripts/relevant-checks.sh` symlink classified as absent → `RELEVANT_CHECKS_SKIPPED` (exit 0)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: A symlink that exists but is broken can be treated like a missing script, emitting SKIPPED with exit 0, so broken consumer wiring can look like an intentional omit-skip and bypass local checks without a distinct failure/reason unless product chooses fail-closed or a dedicated reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add explicit broken-symlink detection and a failure or dedicated reason plus a helper-failure harness assertion.

---


