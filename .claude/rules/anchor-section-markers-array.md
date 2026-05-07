---
paths: ["scripts/anchor-section-markers.sh", "scripts/anchor-section-markers.md", "scripts/assemble-anchor.sh", "scripts/assemble-anchor.md", "scripts/tracking-issue-write.sh", "scripts/tracking-issue-write.md", "scripts/hydrate-anchor.sh", "scripts/hydrate-anchor.md", "scripts/test-tracking-issue-write.sh", "scripts/test-tracking-issue-write.md", "scripts/test-assemble-anchor.sh", "scripts/test-assemble-anchor.md", "scripts/test-hydrate-anchor.sh", "scripts/test-hydrate-anchor.md", "skills/implement/references/anchor-comment-template.md"]
---

# Anchor Section Markers Array

`scripts/anchor-section-markers.sh` is the single source of truth for
the canonical `SECTION_MARKERS` array (assembly / truncation /
hydration order). It is sourced verbatim by three scripts —
`scripts/assemble-anchor.sh`, `scripts/tracking-issue-write.sh`, and
`scripts/hydrate-anchor.sh` — and the human-readable counterpart
`skills/implement/references/anchor-comment-template.md` is maintained
in parallel (it does not source the shell file).

When you add, remove, or reorder a section, update **two** in-tree slug
sets in the same change:

1. `SECTION_MARKERS` in `scripts/anchor-section-markers.sh` — drives
   `assemble-anchor.sh`'s marker-pair walk, `tracking-issue-write.sh`'s
   per-section truncation, and `hydrate-anchor.sh`'s slug allowlist.
2. `COLLAPSE_PRIORITY` in `scripts/tracking-issue-write.sh` — drives
   body-level collapse order. `scripts/test-tracking-issue-write.sh`
   case (i) pins `SECTION_MARKERS ⊆ COLLAPSE_PRIORITY` (every
   `SECTION_MARKERS` slug must appear in `COLLAPSE_PRIORITY`); case
   (i2) is a targeted regression guard that `timing-report` stays
   present in both arrays. The full converse
   (`COLLAPSE_PRIORITY ⊆ SECTION_MARKERS`) is NOT enforced — extra
   stale slugs in `COLLAPSE_PRIORITY` would still pass CI. Adding a
   slug to `SECTION_MARKERS` without updating `COLLAPSE_PRIORITY` does
   fail (i) loudly.

Also update the regression harness fixtures that pin slug expectations:
`scripts/test-tracking-issue-write.sh`, `scripts/test-assemble-anchor.sh`,
and `scripts/test-hydrate-anchor.sh`.

**prevents**: silent skip in the per-section truncation pass and silent
rejection in hydration when a new anchor section is introduced without
updating `SECTION_MARKERS`; loud CI failure with confusing diagnostics
when a slug is added to `SECTION_MARKERS` but not to `COLLAPSE_PRIORITY`.
