---
paths:
  - "skills/shared/topology.tsv"
  - "docs/topology.md"
  - "python/rendering.py"
  - "python/cli.py"
  - "python/decompose.py"
  - "python/plan_scout.py"
  - "python/test_decompose.py"
  - "python/test_plan_scout.py"
  - "skills/design/scripts/design-step2a.sh"
  - "skills/design/references/flags.md"
  - "skills/design/references/plan-review.md"
  - "skills/design/references/decompose-panel.md"
  - "python/plan_quality.py"
  - "skills/implement/references/conflict-resolution.md"
  - "skills/research/references/research-phase.md"
  - "skills/research/references/validation-phase.md"
  - "python/review_pipeline.py"
  - "python/legacy_review_shell/dispatch-panel.sh"
  - "skills/design/scripts/emit-design-plan-preview.sh"
---

# Topology Generation

**Adding/changing a topology count** → update the runtime authority first,
edit `skills/shared/topology.tsv`, then run
`python3 python/cli.py generate topology-docs` to regenerate `docs/topology.md`.
Consumer docs linking to `docs/topology.md` need no edit unless you add a
new row anchor.

Adding a `skills/shared/topology.tsv` row requires extending `paths:` with
the new row's runtime authority file so future edits load this rule.
