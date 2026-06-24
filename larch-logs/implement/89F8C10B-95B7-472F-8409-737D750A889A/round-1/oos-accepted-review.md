### OOS_1: [OUT_OF_SCOPE] Stale plan-review.md severity rubric cross-reference
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/plan-review.md` still points to `approval-gates.md` **Severity classification rubric**, but the branch renamed that section to **Severity classification contract** and removed the old rubric prose. Gate B runtime authority is in the updated `approval-gates.md`; this is stale cross-doc guidance only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update the `plan-review.md` bullet to reference **Severity classification contract** and the three Python verbs.
  - From cursor-specialist-testing-output.txt: Update the bullet to reference **Severity classification contract**.


