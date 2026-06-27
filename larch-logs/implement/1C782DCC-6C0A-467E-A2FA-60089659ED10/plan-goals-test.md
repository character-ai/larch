## Goal
Implement issue #5172: [IMPLEMENTING] [py-code-quality] Packaging 6/9: move design and planning into larch.design.

## Implementation Plan
**Problem.** The `/design` lifecycle is concentrated in `design_lifecycle.py` (4,455 LOC) plus planning helpers, all flat with no package boundary.

**Proposed change.** Move the design subsystem into `larch.design`: `design_lifecycle`, `design_pause`, `design_oos`, `decompose`, `plan_quality`, `plan_scout`, `clarify`. Rewrite all importers to `from larch.design import ...`. Update the `cli.py` `_REGISTRY` `design`, `plan`, `decompose`, and `clarify` entries. Exact module set is finalized in this child's `/design` (and any overlap with the review child's `plan_review*` is resolved there).

**Out of scope / don't-touch.** No behavior change. Keep the invocation contract and all wire formats (issue-anchored plan markers, clarify round-trip grammar). Pure move plus import rewrites.

**Acceptance.** Design modules live under `larch.design`; importers and registry repointed; `make py-lint` / `make py-test` green; consumer invocations unchanged.

**Effort / risk.** Medium / medium.

**Dependencies.** Blocked by the foundation packaging child (1/9). Tracked under umbrella #4982. Wired via `/block-issue`.

## Test plan
(no test plan section in plan-file)
