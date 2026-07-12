## Proposed Design Outline

### Goals
- Bind salvage commit provenance to the lane identity so a subject-only match cannot authorize reship.
- Verify the `Larch-Salvage-Step` trailer in both the regular dispatch path and the crash-finalize path.

### Non-goals
- No changes to the rounds file, lineage file, or other handoff artifacts.
- No new config keys, sidecar files, or step machinery.

### Approach sketch
- Add `\n\nLarch-Salvage-Step: {identity.step}` to the commit message in `_salvage_uncommitted_fixer_edits`.
- In `_validated_salvage_head`, fetch the full commit body with `git show -s --format=%B` and assert the `Larch-Salvage-Step` trailer equals `identity.step`.
- Update `test_crashed_lane_validated_salvage_commit_reships` to include the trailer.
- Add `test_crashed_lane_spoofed_subject_without_trailer_bails` to cover the spoofing scenario.
- Add a brief note to `SECURITY.md`.

### Surfaces in scope
- `python/larch/implement/ci_fixer_lane.py`
- `python/tests/implement/test_ci.py`
- `SECURITY.md`

### Open questions
- None.
