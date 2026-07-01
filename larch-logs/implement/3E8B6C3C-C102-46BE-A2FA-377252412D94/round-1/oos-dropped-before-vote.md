### OOS_1: [OUT_OF_SCOPE] Gate C full-plan emit path mechanism inconsistency
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-gate-contracts
- **Severity**: latent
- **Concern**: Structured **See full plan** / **Other** full-plan paths still disagree on mechanism (`cat` in Large-plan summary vs `python/cli.py plan-review preview --variant full` in Prompt and Other dispatch at `skills/design/references/approval-gates.md:167`, `:198`, `:207`, `:218`). The split predates this branch and was not introduced by the compression pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Align in a separate contract-cleanup issue if desired; out of scope for density-only work.

### OOS_2: [OUT_OF_SCOPE] Gate C option lettering ambiguity
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: At `skills/design/references/approval-gates.md:232`, state invariant 2 still says "Gate C(c)" for manual re-run overwrite semantics while Gate A labels "Gate C option (b)" as discuss further; option lettering is ambiguous across the design skill. Pre-existing.

### OOS_3: [OUT_OF_SCOPE] Architectural-guideline deviation assessment missing Large-plan summary cross-reference
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: At `skills/design/references/approval-gates.md:172`, architectural-guideline deviation assessment no longer cross-references Large-plan summary mode ("chat preview may be outline-only"). The fail-closed "assess … complete on-disk `plan.txt`, not the chat preview" directive remains, so this is resilience margin only, not a broken contract.

### OOS_4: [OUT_OF_SCOPE] Compress commit scope limited to approval-gates.md
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Commit `d4b55d4ad` compresses the approval gates reference (only `skills/design/references/approval-gates.md`).

### OOS_5: [OUT_OF_SCOPE] Branch includes out-of-feature-scope larch-logs artifacts
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-gate-contracts
- **Severity**: nit
- **Concern**: Besides `approval-gates.md`, the branch also adds implement run-log artifacts under `larch-logs/design/3E8B6C3C-.../` (commit `b724cee6f` chore larch-logs flush), outside the prose-compression plan; they do not change gate routing. Validation run: `scripts/test-design-structure.sh`, `test-gate-b-apply-mode.sh`, and `test-step3-review-cap.sh` all pass; `python3 python/cli.py lint skill-closure-growth` passes (design closure 69,234 vs baseline 70,464).

### OOS_6: [OUT_OF_SCOPE] Closure growth lint does not enforce per-file shrink floor
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/skill-closure-baseline.json` closure growth lint only blocks increases above baseline; it does not pin a minimum per-file shrink for `approval-gates.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional follow-up to add a harness floor if ~15% per-file reduction should be mechanically enforced; not required for this feature to ship correctly.

