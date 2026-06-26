### OOS_1: [OUT_OF_SCOPE] Duplicate CI-fix body require needles in structure harness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-structure.sh` duplicates CI-fix body `require` needles that the plan assigns exclusively to `test-implement-step8-exit3-first-fixer.sh`. Duplicate enforcement increases maintenance cost and diverges from the documented harness split without changing runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove the ci_fix_ref body require loop from structure lint; keep parent forbid guards and ordering pins only.

### OOS_2: [OUT_OF_SCOPE] require_near ci-fix vs operator-bail checks proximity only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `require_near` ci-fix vs operator-bail checks proximity only, not mandatory-read-before-sibling-bullet order. Weak pin; plan edge case already documents false-pass risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Prefer ci_fix_slice position asserts over file-global require_near.

### OOS_3: [OUT_OF_SCOPE] Duplicate CI-fix body require needles across harnesses
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Duplicate CI-fix body require needles in structure and exit3-first-fixer harnesses. Plan split drift risk if one harness updates without the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Keep body requires only in test-implement-step8-exit3-first-fixer.sh per plan.

### OOS_4: [OUT_OF_SCOPE] Ambiguous routing after sentinel write failure in ship-pr-ci-fix.md
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing ambiguous fall through after sentinel write failure. Attempt guard may be bypassed without explicit operator-bail routing on sentinel I/O failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clarify terminal routing on sentinel write failure in a follow-up.

### OOS_5: [OUT_OF_SCOPE] exit-matrix checkpoint pointer still targets step-8-oos-checkpoint.md
- **Reviewer(s)**: dyn-dyn-lazy-load-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/references/ship-pr-exit-matrix.md:70` still points checkpoint contract readers at `step-8-oos-checkpoint.md` while router semantics now live in `ship-pr-oos-checkpoint-router.md`; harmonizing those entrypoints would reduce “which doc owns OOS checkpoint routing?” ambiguity, but the split preserved prior layering and did not remove the script contract reference.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Parent forbid needles omitted to avoid reship false positives
- **Reviewer(s)**: dyn-dyn-lazy-load-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-structure.sh:474-510` omits some plan-listed parent forbid needles (e.g. `Its process rc is 0 whenever`, `re-invoke \`step-8-ship.sh\``) because global forbids would false-positive on legitimate every-run reship / execution-issues prose; section-scoped forbid helpers would be a worthwhile follow-up under G-Enf-1, but that is harness hardening rather than a runtime regression introduced here.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Unrelated run-log commit churn on branch
- **Reviewer(s)**: dyn-dyn-lazy-load-output.txt
- **Severity**: nit
- **Concern**: Commit `c361d5062` (`chore(larch-logs): flush ...`) is unrelated run-log churn on an otherwise Markdown/harness-only lazy-load split; it does not affect routing boundaries but adds review noise to the branch.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] SKILL.md fork-before-ci-fix guard asymmetry is plan-scoped
- **Reviewer(s)**: dyn-dyn-harness-pins-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/SKILL.md` has no fork-before-`ship-pr-ci-fix.md` index guard; only `skills/implement/references/ship-pr-exit-matrix.md` enforces that ordering. The plan scoped that pin to the matrix `ci_fix_slice`, so this is a coverage asymmetry, not a current prose bug.
- **Suggested revisions (informational for voters; coder decides)**:

