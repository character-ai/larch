---
paths: ["scripts/anchor-section-markers.sh", "scripts/anchor-section-markers.md", "scripts/assemble-anchor.sh", "scripts/assemble-anchor.md", "scripts/tracking-issue-write.sh", "scripts/tracking-issue-write.md", "scripts/hydrate-anchor.sh", "scripts/hydrate-anchor.md", "scripts/test-tracking-issue-write.sh", "scripts/test-tracking-issue-write.md", "scripts/test-assemble-anchor.sh", "scripts/test-assemble-anchor.md", "scripts/test-hydrate-anchor.sh", "scripts/test-hydrate-anchor.md", "skills/implement/references/anchor-comment-template.md"]
---

# Anchor Section Markers Array

`scripts/anchor-section-markers.sh` is the single source of truth for
the canonical `SECTION_MARKERS` array (assembly / truncation /
hydration order). It is sourced verbatim by
`scripts/assemble-anchor.sh`, `scripts/tracking-issue-write.sh`, and
`scripts/hydrate-anchor.sh`. The human-readable counterpart is
`skills/implement/references/anchor-comment-template.md`.

When you add, remove, or reorder a section in any of those four
consumers, update **two** in-tree slug sets in the same change:

1. `SECTION_MARKERS` in `scripts/anchor-section-markers.sh` — drives
   `assemble-anchor.sh`'s marker-pair walk, `tracking-issue-write.sh`'s
   per-section truncation, and `hydrate-anchor.sh`'s slug allowlist.
2. `COLLAPSE_PRIORITY` in `scripts/tracking-issue-write.sh` — drives
   body-level collapse order. `scripts/test-tracking-issue-write.sh`
   case (i) pins `SECTION_MARKERS ⊆ COLLAPSE_PRIORITY` and case (i2)
   pins the converse, so omitting an update fails CI loudly.

Also update the regression harness fixtures that pin slug expectations:
`scripts/test-tracking-issue-write.sh`, `scripts/test-assemble-anchor.sh`,
and `scripts/test-hydrate-anchor.sh`.

**prevents**: silent skip in the per-section truncation pass and silent
rejection in hydration when a new anchor section is introduced without
updating `SECTION_MARKERS`; loud CI failure with confusing diagnostics
when a slug is added to `SECTION_MARKERS` but not to `COLLAPSE_PRIORITY`.
