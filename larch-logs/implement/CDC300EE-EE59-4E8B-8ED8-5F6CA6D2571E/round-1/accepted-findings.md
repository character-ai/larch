### FINDING_1: CALLER_KIND wire token vs SKILL Exit 5 / NEVER #15
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-consistency-output.txt
- **Concern**: `skills/implement/SKILL.md` (NEVER #15 and the Step 8+ Exit 5 handler) treats the same-version `caller_kind` as `step8_apply_bump_same_version` and/or lists only `step8b_rebase` and `step8_apply_bump_same_version`, while `scripts/ship-pr.sh` still persists `CALLER_KIND=step8b_same_version` on exit 5 (same paths reviewers cited around 784–788). Harnesses such as `scripts/test-ship-pr.sh` (and related docs like `scripts/test-ship-pr.md`) still assert that literal. That breaks the “use the exact `CALLER_KIND` from `ship-pr-state.sh`” contract against the documented enum/wording: strict readers may treat real state as invalid, remap the token, or pick the wrong sub-procedure branch versus the markdown contract.
- **Suggested revision**: Complete the rename in the writer and tests—emit `step8_apply_bump_same_version` from `scripts/ship-pr.sh`, update `scripts/test-ship-pr.sh` / `scripts/test-ship-pr.md` (and any other assertions), and re-grep so the wire value agrees with `SKILL.md` and `skills/implement/references/rebase-rebump-subprocedure.md`; weaker alternative is to document an explicit legacy alias and mapping in Exit 5 / NEVER #15 and the subprocedure until the script changes.


### FINDING_2: Implementation plan verification claim vs repo reality
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The implementation plan’s verification narrative (edge cases / scoped grep) is reported as if only `SKILL.md` still diverged, but `scripts/` (and related harness expectations) still contain `step8b_same_version`, so the stated sign-off/traceability does not match the codebase as described.
- **Suggested revision**: Re-run the intended scoped repo grep (or equivalent), then either extend the change set to match the claim or revise the plan’s verification wording to reflect what is actually present.


