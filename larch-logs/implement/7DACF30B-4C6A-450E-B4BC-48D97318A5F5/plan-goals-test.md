## Goal
Implement issue #5171: [IMPLEMENTING] [py-code-quality] Packaging 5/9: move review and voting into larch.review.

## Implementation Plan
**Problem.** The code-review pipeline, voting, and findings modules are flat with no package boundary, despite being a tightly coupled subsystem. `voting` has 11 importers; the `review_*` files share helpers.

**Proposed change.** Move the review subsystem into `larch.review`: `review_pipeline`, `review_and_fix`, `review_tally`, `review_aggregate`, `review_types`, `voting`, `findings_ledger`, `plan_review`, `plan_review_panel`, `plan_review_round`. Rewrite all importers to `from larch.review import ...`. Update the `cli.py` `_REGISTRY` `review`, `voting`, and `plan-review` entries. Exact module set is finalized in this child's `/design`.

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats (vote tables, TSV findings grammar). Pure move plus import rewrites.

**Acceptance.** Review modules live under `larch.review`; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations unchanged.

**Effort / risk.** Medium / medium.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
