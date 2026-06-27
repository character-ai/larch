---
paths:
  - "skills/shared/topology.tsv"
  - "docs/topology.md"
  - "python/rendering.py"
  - "python/cli.py"
  - "python/decompose.py"
  - "python/plan_scout.py"
  - "python/larch/design/plan_scout.py"
  - "python/test_decompose.py"
  - "python/test_plan_scout.py"
  - "python/design_lifecycle.py"
  - "skills/design/references/flags.md"
  - "skills/deps/SKILL.md"
  - "skills/design/references/plan-review.md"
  - "skills/design/references/decompose-panel.md"
  - "python/plan_quality.py"
  - "python/larch/design/plan_quality.py"
  - "skills/implement/references/conflict-resolution.md"
  - "skills/research/references/research-phase.md"
  - "skills/research/references/validation-phase.md"
  - "python/larch/review/review_pipeline.py"
  - "python/larch/review/plan_review.py"
  - "python/larch/review/plan_review_panel.py"
  - "python/larch/git/pr.py"
  - "python/migrated-scripts.tsv"
---

# Topology Generation

**Adding/changing a topology count** → update the runtime authority first,
edit `skills/shared/topology.tsv`, then run
`python3 python/cli.py generate topology-docs` to regenerate `docs/topology.md`.
Consumer docs linking to `docs/topology.md` need no edit unless you add a
new row anchor.

## `topology.tsv` row constraints

- `composition` must match `[A-Za-z0-9 ./+-]` only.
- `value` must appear verbatim in the row's `runtime_authority`; add new
  values to the authority first, then align `skills/shared/topology.tsv`.

Adding a `skills/shared/topology.tsv` row requires extending `paths:` with
the new row's runtime authority file so future edits load this rule.
