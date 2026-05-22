### OOS_1: lib-title-markers.md stub should mention [PLANNED]
- **Description**: `scripts/lib-title-markers.md` is a stub that says "see tracking-issue-write.md for grammar". Adding `[PLANNED]` to `lib-title-markers.sh`'s `insert_signal_marker` should be reflected in the stub to avoid drift. File: `scripts/lib-title-markers.md`.
- **Reviewer**: Cursor-Edge, Cursor-Innovation
- **Phase**: design


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_2: CHANGELOG.md rename-states prose omits planned
- **Description**: `CHANGELOG.md` narrative around rename states lists only `in-progress|done|stalled`; after shipping `planned`, the changelog entry for the release would be incomplete. File: `CHANGELOG.md`.
- **Reviewer**: Cursor-Requirements
- **Phase**: design

---

Vote format: one line per finding — e.g. `FINDING_1: YES`, `FINDING_2: NO`, `FINDING_3: EXONERATE`, `OOS_1: YES`.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

