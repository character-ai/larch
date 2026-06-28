### OOS_1: [OUT_OF_SCOPE] Operator docs can drift from relocated auto error reporting surfaces
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-design-prose
- **Severity**: nit
- **Concern**: `docs/configuration-and-permissions.md` still carries a parallel `/design auto error reporting` section that this relocation did not update. After merge, operator docs may disagree with plugin `SKILL.md` / `finalize-step5.md` reference surfaces (`SKILL.md`, `finalize-step5.md`, and `docs/` can drift).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update operator docs in a follow-up issue.
  - From cursor-specialist-edge-cases: **Suggested fix:** Follow-up doc sync or a cross-link to the reference file.

### OOS_2: [OUT_OF_SCOPE] finalize-step5.md reference header metadata does not mention failure-report debugging load paths
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `skills/design/references/finalize-step5.md` **When to load** / **Contract** still describe Step 5 entry only, while `skills/design/SKILL.md` also allows load when debugging failure reporting. The top-level Contract header still lists only Step 5 finalization surfaces and does not mention teardown auto error reporting even though that content now lives in the same file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: **Suggested fix:** Extend the reference `When to load` line to include failure-report debugging, or keep SKILL-only guidance explicit.
  - From cursor-specialist-testing: **Suggested fix:** Extend the Contract paragraph when next editing the reference header.

### OOS_3: [OUT_OF_SCOPE] No structural harness pins guard relocated auto-error-reporting or folded-contract prose
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Prior `finalize-step5.md` relocations use paired `contains "$FINALIZE_STEP5_MD"` / `not_contains "$SKILL_MD"` pins, but this move adds no similar pins for `## /design auto error reporting`, so re-duplicating that block in `SKILL.md` would not fail CI. The new `## Folded contract and tradeoff` section in `sentinel-host-table.md` also has no structural harness pin; only the maintainer pointer in `SKILL.md` guards against total loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: **Suggested fix:** Add positive/negative harness pins in a follow-up if you want mechanical enforcement per G-Enf-1.
  - From cursor-specialist-testing: **Suggested fix:** Optional `contains` pin in `test-design-structure.sh` if you want relocation regression coverage similar to other md-to-py-VIII moves.

