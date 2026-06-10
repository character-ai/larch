# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Stall seed key-list pointer cites Step 5 instead of canonical Step 8
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-cross-doc-consistency-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/review-implement-step5-loop.md:19` points the stall-seed `ship-pr-state.sh` required-key list at `skills/implement/SKILL.md` Step 5, but reviewers agree the canonical key list is the Step 8 `write-initial-state-keys` block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Point the sentence to skills/implement/SKILL.md Step 8 write-initial-state-keys for the key list, and keep skills/implement/references/step5-review-branches.md as the stall branch body reference.
  - From codex-specialist-correctness-output.txt: Reword the citation to point to skills/implement/SKILL.md Step 8 write-initial-state-keys block for keys and skills/implement/references/step5-review-branches.md for the stall branch body.
  - From codex-specialist-edge-cases-output.txt: Point the key list reference at skills/implement/SKILL.md Step 8 write-initial-state-keys block and keep the stall branch body pointer at skills/implement/references/step5-review-branches.md.
  - From codex-specialist-testing-output.txt: Cite skills/implement/SKILL.md Step 8 / write-initial-state-keys for the key list, and keep skills/implement/references/step5-review-branches.md as the stall branch body authority.
  - From dyn-cross-doc-consistency-output.txt: Change the key-list pointer to Step 8 (or cite the `write-initial-state-keys` anchor directly), e.g. `key list in skills/implement/SKILL.md` Step 8 `<!-- write-initial-state-keys:begin/end -->`, keeping the stall body pointer at `skills/implement/references/step5-review-branches.md`.


### FINDING_4: Issue-anchored plan still gives conflicting Preflight rubric authority
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-ref-completeness-output.txt, dyn-cross-doc-consistency-output.txt
- **Severity**: latent
- **Concern**: `docs/issue-anchored-plan.md` now points the Plan adequacy section to `skills/implement/references/preflight-plan-audit.md`, but later Non-Scope / See also references still point readers to `skills/implement/SKILL.md` for the same rubric or adequacy-audit authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Retarget the Non-Scope bullets to skills/implement/references/preflight-plan-audit.md for the fixed rubric, leaving skills/implement/SKILL.md as the orchestration and Preflight call-site authority.
  - From cursor-specialist-correctness-output.txt: Update line 288 to reference skills/implement/references/preflight-plan-audit.md consistently with the Plan adequacy section.
  - From codex-specialist-correctness-output.txt: Change the bullet to cite skills/implement/references/preflight-plan-audit.md for the fixed Preflight rubric and reserve skills/implement/SKILL.md for orchestration flow.
  - From cursor-specialist-edge-cases-output.txt: Retarget line 288 to skills/implement/references/preflight-plan-audit.md to match line 187.
  - From codex-specialist-edge-cases-output.txt: Update the remaining references to cite skills/implement/references/preflight-plan-audit.md for the fixed audit rubric and keep skills/implement/SKILL.md as the orchestration/Step 0 pointer.
  - From codex-specialist-testing-output.txt: Retarget the plan-quality/rubric references to skills/implement/references/preflight-plan-audit.md, while keeping skills/implement/SKILL.md only for orchestration/preflight flow details.
  - From dyn-ref-completeness-output.txt: Update lines 288–292 to cite `skills/implement/references/preflight-plan-audit.md` for rubric content and keep `skills/implement/SKILL.md` only for Preflight orchestration (admission, `plan-block-read.sh`, clarify posting, exit codes); add `preflight-plan-audit.md` to § “See also” (line 298) alongside the SKILL Preflight pointer.
  - From dyn-cross-doc-consistency-output.txt: Update lines 288, 292, and 298 to cite `skills/implement/references/preflight-plan-audit.md` for rubric/adequacy-audit authority (reserve `skills/implement/SKILL.md` references for orchestration items like clarify refuse bullets and NEVER rules that remain there).


