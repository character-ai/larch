## Proposed Design Outline

### Goals
- One Bash fence enters Step 5 (fold `design-step5.sh` prelude into `design-step5b-prepare.sh`).
- Summary emission needs no separate Read call; orchestrator gets body from stdout markers.
- Verbatim-emission contract stays intact: file still written, gates preserved, no free-form recap.

### Non-goals
- Converting `REPORT_GATE_SIDECARS_FILE` to markers.
- Changes to other design steps or other scripts.
- Changing when or how `render-final-summary.sh` is invoked.

### Approach sketch
- Move `.completed/step-4b` write, pause check, and timing mark from `design-step5.sh` to the head of `design-step5b-prepare.sh`.
- Remove the `design-step5.sh` Bash fence from SKILL.md; update the Step 5 breadcrumb/sentinel table.
- Update SKILL.md Step 5b OOS bridge prose: Write-tool directive instead of shell `printf`.
- Emit `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` in `design-step5c.sh` (all exit paths) and `design-step-final-summary.sh` (after render).
- Update SKILL.md Step 5c item 5 and Final summary block: parse body from stdout markers; file Read as fallback.
- Extend `test-design-publish.sh` and `test-design-structure.sh`.

### Surfaces in scope
- `skills/design/scripts/design-step5.sh` (content moved + script kept as stub or deleted)
- `skills/design/scripts/design-step5b-prepare.sh`
- `skills/design/scripts/design-step5c.sh`
- `skills/design/scripts/design-step-final-summary.sh`
- `skills/design/SKILL.md`
- `skills/design/scripts/test-design-publish.sh`
- `scripts/test-design-structure.sh`

### Open questions
- Keep `design-step5.sh` as a pass-through stub (backward compat for paused sessions) or delete it?
