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

**Adding/changing a topology count** → first ensure the runtime authority for that count is updated; then edit `skills/shared/topology.tsv`; then run `bash scripts/generate-topology-docs.sh` to regenerate `docs/topology.md`. Consumer docs that link to `docs/topology.md` need no edit unless a new row anchor is being introduced.

Adding a new row to `skills/shared/topology.tsv` requires extending this rule's `paths:` to include the new row's runtime authority file, so future edits to that file load this rule.
