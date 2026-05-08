---
paths:
  - "skills/shared/topology.tsv"
  - "docs/topology.md"
  - "scripts/generate-topology-docs.sh"
  - "scripts/generate-topology-docs.md"
  - "skills/design/references/sketch-launch.md"
  - "skills/design/references/flags.md"
  - "skills/design/references/plan-review.md"
  - "skills/shared/dialectic-protocol.md"
  - "skills/implement/references/conflict-resolution.md"
  - "skills/research/references/research-phase.md"
  - "skills/research/references/validation-phase.md"
---

# Topology Generation

**Adding/changing a topology count** → update the runtime authority first,
edit `skills/shared/topology.tsv`, then run
`bash scripts/generate-topology-docs.sh` to regenerate `docs/topology.md`.
Consumer docs linking to `docs/topology.md` need no edit unless you add a
new row anchor.

Adding a `skills/shared/topology.tsv` row requires extending `paths:` with
the new row's runtime authority file so future edits load this rule.
