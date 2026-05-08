---
paths: ["scripts/anchor-section-markers.sh", "scripts/anchor-section-markers.md", "scripts/assemble-anchor.sh", "scripts/assemble-anchor.md", "scripts/tracking-issue-write.sh", "scripts/tracking-issue-write.md", "scripts/hydrate-anchor.sh", "scripts/hydrate-anchor.md", "scripts/test-tracking-issue-write.sh", "scripts/test-tracking-issue-write.md", "scripts/test-assemble-anchor.sh", "scripts/test-assemble-anchor.md", "scripts/test-hydrate-anchor.sh", "scripts/test-hydrate-anchor.md", "skills/implement/references/anchor-comment-template.md"]
---

# Anchor Section Markers Array

`scripts/anchor-section-markers.sh` is the source of truth for
`SECTION_MARKERS` (assembly / truncation / hydration order). It is
sourced verbatim by `scripts/assemble-anchor.sh`,
`scripts/tracking-issue-write.sh`, and `scripts/hydrate-anchor.sh`;
`skills/implement/references/anchor-comment-template.md` is the parallel
human counterpart and does not source the shell file.

When adding, removing, or reordering a section, update both slug sets in
the same change:

1. `SECTION_MARKERS` in `scripts/anchor-section-markers.sh` — drives
   `assemble-anchor.sh` marker-pair walks, `tracking-issue-write.sh`
   per-section truncation, and `hydrate-anchor.sh` slug allowlist.
2. `COLLAPSE_PRIORITY` in `scripts/tracking-issue-write.sh` — drives
   body-level collapse order. `scripts/test-tracking-issue-write.sh`
   case (i) pins `SECTION_MARKERS ⊆ COLLAPSE_PRIORITY`; every
   `SECTION_MARKERS` slug must appear in `COLLAPSE_PRIORITY`. Case
   (i2) pins `timing-report` in both arrays. The converse
   (`COLLAPSE_PRIORITY ⊆ SECTION_MARKERS`) is NOT enforced; stale extra
   slugs in `COLLAPSE_PRIORITY` pass CI. Adding a `SECTION_MARKERS` slug
   without updating `COLLAPSE_PRIORITY` fails (i) loudly.

Update slug fixtures in `scripts/test-tracking-issue-write.sh`,
`scripts/test-assemble-anchor.sh`, and `scripts/test-hydrate-anchor.sh`.

**prevents**: silent per-section truncation skips and hydration rejection
when a new anchor section omits `SECTION_MARKERS`; loud CI failure with
confusing diagnostics when `SECTION_MARKERS` gains a slug missing from
`COLLAPSE_PRIORITY`.
