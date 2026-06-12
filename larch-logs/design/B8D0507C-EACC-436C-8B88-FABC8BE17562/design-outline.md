## Proposed Design Outline

### Goals
- Add a mermaid Gantt timing chart per completed review round to the Review Phase Detail section.
- Show "No review rounds completed." when no rounds ran, instead of rendering nothing.

### Non-goals
- No changes to architecture diagram generation (Step 3b).
- No new `larch:diagrams` tracked diagram artifacts; Gantt charts live only in the final summary note.
- No changes to how timing data is recorded (timing ledger writers are untouched).

### Approach sketch
- Modify `scripts/render-review-phase-detail.sh`: change the "no rounds" branch from `finalize_empty` to a message; add per-round Gantt generation using vendor rows from `timing-ledger.tsv`.
- Each Gantt block uses `dateFormat X`, `axisFormat %M:%S`, timestamps normalized to seconds since round start.
- Label each bar via the existing `slot_map` lookup and `derive.awk` fallback.
- Cap tasks per round at 25.
- Update sibling `.md` doc and harness `test-render-review-phase-detail.sh`.

### Surfaces in scope
- `scripts/render-review-phase-detail.sh`
- `scripts/render-review-phase-detail.md`
- `scripts/test-render-review-phase-detail.sh`

### Open questions
- None.
