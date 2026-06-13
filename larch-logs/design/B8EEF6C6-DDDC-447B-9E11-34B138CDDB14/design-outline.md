## Proposed Design Outline

### Goals
- Move the non-architectural plan classifier from SKILL.md prose into `design-step3b-entry.sh`, which emits `DIAGRAM_REQUIRED=` and handles the full skip path internally in one call.
- Expand `design-step3b-sanitize.sh` to absorb candidate promotion, failure-path cleanup, failure-log append, and the Step 3b completion boundary (FINALIZE + `.completed/step-3b`).
- Introduce `design-step3b-tail.sh` combining Step 4 timing, compat FINALIZE guard, rejected-findings emit (between stable markers), Step 4b timing, Gate C preview, and `SKIP_APPROVE_REQUESTED` read.
- Add `--variant full` to `emit-design-plan-preview.sh` to replace the raw `cat plan.txt` in the Gate C "See full plan" branch.

### Non-goals
- No change to Step 3 review, Gate B, Gate C `AskUserQuestion` logic, or pause/resume protocol.
- No changes to scripts outside `skills/design/scripts/` (except SKILL.md and `test-design-structure.sh`).
- No backward-compatibility stubs for retired scripts; sessions resume correctly through existing sentinels.

### Approach sketch
- Revise `design-step3b-entry.sh`: add awk/grep classifier over `plan.txt` headings; on non-architectural emit DIAGRAM_REQUIRED=false + skip cleanup + FINALIZE + write `.completed/step-3b`; on architectural emit DIAGRAM_REQUIRED=true + cleanup.
- Revise `design-step3b-sanitize.sh`: on success promote candidate + emit diagram between `---LARCH-DIAGRAM-BEGIN---` / `---LARCH-DIAGRAM-END---` markers + FINALIZE + write `.completed/step-3b`; on failure cleanup + failure-log append.
- Write `design-step3b-tail.sh` (+ sibling `.md`): Step 4 timing + compat FINALIZE guard + emit `rejected-findings.md` between `---LARCH-REJECTED-BEGIN---` / `---LARCH-REJECTED-END---` + Step 4b timing + Gate C preview + SKIP_APPROVE_REQUESTED read + `.completed/step-4` write.
- Add `--variant full` arm to `emit-design-plan-preview.sh`: cat full `plan.txt` under `## Final Design Plan`.
- Update SKILL.md Steps 3b–4b: replace 5+ bash fences with new call sequence; retire stale wrapper-inventory entries.
- Update `test-design-structure.sh`: adjust assertions for revised scripts, add tail wrapper assertions.
- Retire `design-step3b-complete.sh`, `design-step4.sh`, `design-step4b.sh`, `design-step4b-preview.sh`, `design-step4b-read.sh`.

### Surfaces in scope
- `skills/design/scripts/design-step3b-entry.sh` (revised)
- `skills/design/scripts/design-step3b-sanitize.sh` (revised)
- `skills/design/scripts/design-step3b-tail.sh` (new) + `design-step3b-tail.md`
- Retired: `design-step3b-complete.sh`, `design-step4.sh`, `design-step4b.sh`, `design-step4b-preview.sh`, `design-step4b-read.sh`
- `skills/design/scripts/emit-design-plan-preview.sh` + `emit-design-plan-preview.md` (revised)
- `skills/design/SKILL.md` (Step 3b–4b call sites + wrapper inventory)
- `scripts/test-design-structure.sh` (structural assertions)

### Open questions
- None.
