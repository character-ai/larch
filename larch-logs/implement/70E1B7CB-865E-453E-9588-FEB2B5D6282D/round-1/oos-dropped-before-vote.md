### OOS_1: [OUT_OF_SCOPE] Plan compression and frozen-contract criteria met
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The diff matches the approved plan: `design-outline.md` compressed (144→122 lines; ~2,157 est. tokens, target ≤2,162; ~15.2% reduction), `python/skill-closure-baseline.json` regenerated with consistent `/design` closure drop (59375→58991), frozen contract literals preserved (banner, `AskUserQuestion` strings, skip breadcrumbs, cancel-hygiene trio, schema fence, same-turn Step 2b routing, `Read skills/design/references/readability-style.md` at line 33, Consumer/Contract/When-to-load triplet for `test-references-headers.sh`), and local harnesses pass (`test_committed_baseline_matches_fresh_scan`, `lint skill-closure-growth --skill design`, `make test-design-structure`, `make lint-readability-preamble`). Binding-convention removal is acceptable in-scope per plan (redundant with Contract; not CI-pinned for design references).

### OOS_2: [OUT_OF_SCOPE] Step 3 downstream contract cites deleted plan-review-loop.sh
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Step 3 downstream contract still cites deleted `plan-review-loop.sh`. Maintainers debugging scope-anchor behavior may look for a script that no longer exists; anchoring is implemented in `python/larch/review/plan_review.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Update the Step 3 bullet to name plan-review step3-entry / plan_review.py when doing a follow-up doc fix.

### OOS_3: [OUT_OF_SCOPE] Binding convention header removed while peer references retain it
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-outline-contract
- **Severity**: nit
- **Concern**: The `**Binding convention**:` header present on `main` was removed from `design-outline.md` while peer design references (`flags.md`, `approval-gates.md`, `discussion-rounds.md`, and others) still use it. No runtime failure and no design harness currently enforces it, but this creates header-schema drift across design reference files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Re-add a one-line Binding convention header or accept intentional omission in a separate style decision.
  - From cursor-specialist-testing: restore a one-line binding convention or document that `design-outline.md` is intentionally exempt.

### OOS_4: [OUT_OF_SCOPE] Load-bearing breadcrumb literals lack mechanical CI pins
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Cancel hygiene has plan-mandated `rg` gates, but entry-guard skip breadcrumbs, approve/auto-approve success lines, and Refine-loop rules have no mechanical CI pins:unlike `/review` references’ `**Binding convention**:` header check in `scripts/test-review-structure.sh`. This implementation preserved those literals; future density passes could drift them while aggregate closure ratchet still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: add a small structural pin (grep or harness) for the load-bearing breadcrumb set if this file will be compressed again.

### OOS_5: [OUT_OF_SCOPE] Per-file ~15% token gate is manual-only with minimal headroom
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The per-file ~15% gate in `python/larch/lint/lint_skill_closure_growth.py` is manual-only; CI enforces one-directional aggregate growth. This branch meets the manual gate (2,157 ≤ 2,162) with only ~5 tokens of headroom, so a small future edit could miss acceptance without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: optional per-file floor in closure tooling if these compressions become routine.

### OOS_6: [OUT_OF_SCOPE] Branch commit adds out-of-plan larch-logs artifacts
- **Reviewer(s)**: dyn-dyn-outline-contract
- **Severity**: nit
- **Concern**: Branch commit `3b7c4a8e5` adds `larch-logs/implement/70E1B7CB-...` run artifacts. That is outside the plan scope (`design-outline.md` + `skill-closure-baseline.json`) and will inflate the PR diff unless split or dropped before merge.

