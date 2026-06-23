## Proposed Design Outline

### Goals
- Eliminate the ~4 near-verbatim copies of the final-summary marker-extraction instruction in `skills/design/SKILL.md`; the canonical procedure appears exactly once.
- Every emit site (and the brief mentions) references the single source; runtime behavior is byte-for-byte equivalent.

### Non-goals
- No Python migration: the body emit stays orchestrator-side because tool output lands in a collapsible block.
- No change to which completed output each site extracts from, the stop-vs-continue-vs-emit-before-footer after-action, or the `REPORT_GATE_SIDECARS_FILE` follow-on.
- No edits to `/implement` or other skills' summary mechanisms.

### Approach sketch
- Create `skills/shared/final-summary-emit.md` holding the canonical common core: marker extraction (`LARCH_FINAL_SUMMARY_BEGIN`/`END`), `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` Read fallback, verbatim / no-paraphrase emit, the never-via-Bash/Python-tool-call rule, and the `REPORT_GATE_SIDECARS_FILE` follow-on.
- Replace the 4 full copies (Step 0b cancel-route, Final summary block, Step 5c item 5, Step 5c abort path) with a compact pointer to the shared file plus each site's own source + after-action glue kept inline.
- Repoint the brief Anti-halt reminder mention and other partial paraphrases to the same source.
- Preserve load-bearing availability so the orchestrator still follows the procedure at terminal/cancel points without a behavioral gap.

### Surfaces in scope
- `skills/design/SKILL.md` — the 4 full copies + brief mentions
- `skills/shared/final-summary-emit.md` — new shared reference

### Open questions
- None.
