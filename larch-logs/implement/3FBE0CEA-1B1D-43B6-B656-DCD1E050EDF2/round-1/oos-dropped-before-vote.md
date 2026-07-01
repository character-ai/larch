### OOS_1: [OUT_OF_SCOPE] Step 3 harness path typo remains misleading
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: nit
- **Concern**: The Step 3 harness contract still references `test-python/design_lifecycle.py`, which does not match a repo path. This typo was already present before the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: if that is intended to reference the lifecycle tests, rename it to `python/test_design_lifecycle.py`.

### OOS_2: [OUT_OF_SCOPE] Step 0a anti-pattern detail was compressed away
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Step 0a kept the single-block rule but lost explicit subshell/path-collapse anti-pattern detail. Rare mis-split Bash fences could reintroduce unbound `DESIGN_TMPDIR` or `/source-env.sh` collapse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Restore the concise anti-pattern sentence if compaction-resilience duplication is still desired.

### OOS_3: [OUT_OF_SCOPE] Plan helper contracts dropped drift-baseline and related prose
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan helper contracts are thinner than `main`, including the missing standalone `plan-review drift-baseline` citation and reduced optional-trailers prose. Reviewers noted limited direct runtime impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Re-add the drift-baseline literal in the helper contracts block if sibling-contract completeness is required.

### OOS_4: [OUT_OF_SCOPE] Token and baseline validation passed
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-skill-contracts
- **Severity**: nit
- **Concern**: Reviewer observations report that the token target was met, closure `files` membership stayed unchanged, and the baseline was regenerated with the expected unchanged `implement` row.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Structural pin spot-checks passed
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Reviewer spot-checks found key `test-design-structure.sh` literals still present in current `SKILL.md`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Planned design-skill-compress check site is not registered
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan lists `python3 python/cli.py checks run-relevant --site design-skill-compress`, but that site is not registered. Existing changed-file mapping still covers `skills/design/SKILL.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Treat `design-skill-compress` as aspirational or add the site only if you want a dedicated alias; not required for this PR to be testable.

### OOS_7: [OUT_OF_SCOPE] Persist-retally citation removal is net neutral
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Step 3 no longer names `plan-review persist-retally-env` as the purpose of `test_plan_review_panel.py`, while the module remains listed. The reviewer characterized this as net neutral for regression risk.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Step 0a presence/binary key carve-out was already absent
- **Reviewer(s)**: dyn-dyn-skill-contracts
- **Severity**: nit
- **Concern**: The approved plan’s carve-out for the exact Step 0a “presence keys / binary-found keys” sentence appears already absent on `origin/main`; this branch did not introduce the gap.
- **Suggested revisions (informational for voters; coder decides)**:

