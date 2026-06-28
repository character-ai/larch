## Proposed Design Outline

### Goals
- Prevent Gantt chart truncation in the `/design` final summary chat display.
- Ensure all round timing charts are emitted complete to chat, matching what is published to the GitHub comment.

### Non-goals
- Not changing the Gantt rendering logic (`render_gantt`, `render_phase_detail`).
- Not changing what is posted to the GitHub comment (the `tracking-issue upsert-summary` path is unaffected).
- Not removing Gantt charts from the chat display.

### Approach sketch
- Root cause: `_emit_final_summary_marked_from_disk` writes the full `final-summary.md` (~8 KB) to the contract stream (fd 3); Claude Code truncates long task notification outputs, corrupting middle rows of code-fence Gantt blocks.
- Fix the contract stream output: strip the content body from the `LARCH_FINAL_SUMMARY_BEGIN/END` block (emit only the markers as a readiness signal), and emit `FINAL_SUMMARY_PATH` as a KV so the orchestrator knows where to read.
- Switch the `/design` callsite in `final-summary-emit.md` from "Read fallback allowed when marker fails" to "always Read from `${FINAL_SUMMARY_PATH}`".
- Update `SKILL.md` wording for Step 5c / Final summary block to reflect the Read-always behavior.

### Surfaces in scope
- `python/larch/design/design_lifecycle.py` (`_emit_final_summary_marked_from_disk`)
- `skills/shared/final-summary-emit.md`
- `skills/design/SKILL.md` (narrow wording update to the final summary emit prose)

### Open questions
- None.
