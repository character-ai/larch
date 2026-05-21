Here is the normalized structured finding list (merged by shared behavioral risk; distinct items kept separate; `[OUT_OF_SCOPE]` preserved where any merged source used it).

```text
### FINDING_1: CALLER_KIND wire token vs SKILL Exit 5 / NEVER #15
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-consistency-output.txt
- **Concern**: `skills/implement/SKILL.md` (NEVER #15 and the Step 8+ Exit 5 handler) treats the same-version `caller_kind` as `step8_apply_bump_same_version` and/or lists only `step8b_rebase` and `step8_apply_bump_same_version`, while `scripts/ship-pr.sh` still persists `CALLER_KIND=step8b_same_version` on exit 5 (same paths reviewers cited around 784–788). Harnesses such as `scripts/test-ship-pr.sh` (and related docs like `scripts/test-ship-pr.md`) still assert that literal. That breaks the “use the exact `CALLER_KIND` from `ship-pr-state.sh`” contract against the documented enum/wording: strict readers may treat real state as invalid, remap the token, or pick the wrong sub-procedure branch versus the markdown contract.
- **Suggested revision**: Complete the rename in the writer and tests—emit `step8_apply_bump_same_version` from `scripts/ship-pr.sh`, update `scripts/test-ship-pr.sh` / `scripts/test-ship-pr.md` (and any other assertions), and re-grep so the wire value agrees with `SKILL.md` and `skills/implement/references/rebase-rebump-subprocedure.md`; weaker alternative is to document an explicit legacy alias and mapping in Exit 5 / NEVER #15 and the subprocedure until the script changes.

### FINDING_2: Implementation plan verification claim vs repo reality
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The implementation plan’s verification narrative (edge cases / scoped grep) is reported as if only `SKILL.md` still diverged, but `scripts/` (and related harness expectations) still contain `step8b_same_version`, so the stated sign-off/traceability does not match the codebase as described.
- **Suggested revision**: Re-run the intended scoped repo grep (or equivalent), then either extend the change set to match the claim or revise the plan’s verification wording to reflect what is actually present.

### FINDING_3: No recorded /relevant-checks evidence on the change artifact
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The diff/plan material cited gives no evidence that `/relevant-checks` (or equivalent local validation) was run; if CI is not treated as the authoritative substitute, merge could proceed without the promised lint gate.
- **Suggested revision**: Confirm the checks ran in CI and point to that evidence, or attach local `/relevant-checks` results with the change.

### FINDING_4: [OUT_OF_SCOPE] Archived plan-goals line is misleading metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-token-consistency-output.txt
- **Concern**: `larch-logs/implement/CDC300EE-EE59-4E8B-8ED8-5F6CA6D2571E/plan-goals-test.md` (notably bullet/occurrence 2 around lines 12–13) reproduces a copy-paste/identity-style arrow where `step8b_same_version` appears on both sides or otherwise fails to show the intended replacement, which misleads post-hoc audits of what this implement run aimed to edit; some sources treat this as archival/run-log noise rather than executable behavior.
- **Suggested revision**: If log accuracy matters, fix the plan line in a follow-up log commit or corrected source before flush; otherwise explicitly accept as benign archive noise in process docs.

### FINDING_5: [OUT_OF_SCOPE] Pre-existing mismatch between subprocedure naming and ship-pr emission
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: Latent architecture drift: canonical naming in `skills/implement/references/rebase-rebump-subprocedure.md` vs `step8b_same_version` emitted by `scripts/ship-pr.sh` predates / is not solely introduced by the SKILL alignment on this branch; future work should rename the emitter or formally alias both in code and docs.
- **Suggested revision**: Track a follow-up PR to align `ship-pr` emission with the subprocedure contract or document explicit alias equivalence in both places.

### FINDING_6: [OUT_OF_SCOPE] Older implement run logs retain historical token mentions
- **Reviewer(s)**: dyn-token-consistency-output.txt
- **Concern**: Older logs under `larch-logs/implement/E9C19A47-*/` still mention `step8b_same_version` in review/out-of-scope style artifacts; this is historical snapshot content, not part of the live runtime contract surface.
- **Suggested revision**: None required for runtime correctness; only clean up if repository policy demands revising historical log snapshots.

### FINDING_7: [OUT_OF_SCOPE] Self-contradictory written implementation_plan occurrence 2
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The user-authored `implementation_plan` occurrence 2 line is internally inconsistent; reviewers note merged `SKILL` content may still reflect the real objective despite the bad plan line.
- **Suggested revision**: Clean up plan authoring in the tracking issue or design export when convenient; low impact if implementation already matched intent.
```
